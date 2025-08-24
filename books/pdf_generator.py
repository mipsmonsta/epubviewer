import os
import tempfile
import re
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from bs4 import BeautifulSoup
from .models import Book, Chapter

class PDFGenerator:
    """Service class for generating PDFs from EPUB content"""
    
    def __init__(self, book_instance):
        self.book = book_instance
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for different formats"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Author style
        self.author_style = ParagraphStyle(
            'CustomAuthor',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        # Chapter title style
        self.chapter_title_style = ParagraphStyle(
            'CustomChapterTitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            spaceBefore=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            firstLineIndent=20
        )
        
        # Mobile body style
        self.mobile_body_style = ParagraphStyle(
            'MobileBody',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=14,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            firstLineIndent=15
        )
    
    def generate_pdf(self, format_type='standard', quality='standard'):
        """
        Generate PDF from book content
        
        Args:
            format_type: 'standard' or 'mobile'
            quality: 'standard', 'high', or 'print'
        """
        # Get all chapters ordered by sequence
        chapters = self.book.chapters.all().order_by('order')
        
        if not chapters.exists():
            raise ValueError("No chapters found for this book")
        
        # Create PDF file
        pdf_path = self._create_pdf_path(format_type, quality)
        
        # Generate PDF content
        self._generate_pdf_content(pdf_path, chapters, format_type, quality)
        
        return pdf_path
    
    def _create_pdf_path(self, format_type, quality):
        """Create PDF file path"""
        # Create safe filename
        safe_title = re.sub(r'[^\w\-_.]', '_', self.book.title)
        pdf_filename = f"{safe_title}_{format_type}_{quality}.pdf"
        
        # Create PDF directory if it doesn't exist
        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        
        return os.path.join(pdf_dir, pdf_filename)
    
    def _generate_pdf_content(self, pdf_path, chapters, format_type, quality):
        """Generate PDF content using ReportLab"""
        # Choose page size based on format
        if format_type == 'mobile':
            # Custom mobile size (narrower width)
            page_size = (4.5 * inch, 7 * inch)  # Mobile-like proportions
        else:
            page_size = A4
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=page_size,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=1.0 * inch  # Increased bottom margin for page numbers
        )
        
        # Build story (content)
        story = []
        
        # Title page
        story.extend(self._create_title_page())
        story.append(PageBreak())
        
        # Chapters (skip table of contents)
        for i, chapter in enumerate(chapters, 1):
            story.extend(self._create_chapter_content(chapter, i, format_type))
            if i < len(chapters):  # Don't add page break after last chapter
                story.append(PageBreak())
        
        # Build PDF with page numbering
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
    
    def _create_title_page(self):
        """Create title page content"""
        story = []
        
        # Title
        title_text = f"<b>{self.book.title}</b>"
        story.append(Paragraph(title_text, self.title_style))
        
        # Author
        author_text = f"by {self.book.author or 'Unknown Author'}"
        story.append(Paragraph(author_text, self.author_style))
        
        # Generation info
        generation_text = f"Generated on {self.book.uploaded_at.strftime('%B %d, %Y')}"
        story.append(Paragraph(generation_text, self.author_style))
        
        return story
    
    def _create_toc_page(self, chapters):
        """Create table of contents page"""
        story = []
        
        # TOC title
        toc_title = Paragraph("Table of Contents", self.title_style)
        story.append(toc_title)
        story.append(Spacer(1, 20))
        
        # TOC entries (use original chapter titles without numbering)
        for chapter in chapters:
            toc_entry = chapter.title
            story.append(Paragraph(toc_entry, self.body_style))
            story.append(Spacer(1, 5))
        
        return story
    
    def _create_chapter_content(self, chapter, chapter_num, format_type):
        """Create chapter content"""
        story = []
        
        # Chapter title (use original title without adding chapter number)
        chapter_title = chapter.title
        story.append(Paragraph(chapter_title, self.chapter_title_style))
        
        # Chapter content (remove the chapter title from content to avoid duplication)
        content = self._extract_text_content(chapter.content, chapter_title)
        paragraphs = content.split('\n\n')
        
        # Choose style based on format
        body_style = self.mobile_body_style if format_type == 'mobile' else self.body_style
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                # Clean up paragraph text
                paragraph = self._clean_text(paragraph)
                if paragraph:
                    story.append(Paragraph(paragraph, body_style))
                    story.append(Spacer(1, 5))
        
        return story
    
    def _extract_text_content(self, html_content, chapter_title=None):
        """Extract plain text from HTML content using BeautifulSoup"""
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove all style and script tags
            for tag in soup(['style', 'script']):
                tag.decompose()
            
            # Remove the epub-content wrapper div if present
            epub_content = soup.find('div', class_='epub-content')
            if epub_content:
                soup = epub_content
            
            # Get text content
            text = soup.get_text()
            
            # Clean up the text
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                # Only include lines with substantial content
                if line and len(line) > 5 and re.search(r'[a-zA-Z]', line):
                    # Clean up whitespace
                    line = re.sub(r'\s+', ' ', line).strip()
                    cleaned_lines.append(line)
            
            # Join lines into paragraphs
            result = '\n\n'.join(cleaned_lines)
            
            # Remove chapter title from content if provided to avoid duplication
            if chapter_title and result:
                # Try to remove the chapter title from the beginning of the content
                title_patterns = [
                    chapter_title,
                    chapter_title.strip(),
                    chapter_title.upper(),
                    chapter_title.lower(),
                    chapter_title.title(),
                ]
                
                for pattern in title_patterns:
                    if result.startswith(pattern):
                        result = result[len(pattern):].strip()
                        break
                
                # Also try to remove it if it appears as a separate paragraph
                paragraphs = result.split('\n\n')
                filtered_paragraphs = []
                for para in paragraphs:
                    para_stripped = para.strip()
                    # Skip paragraphs that match the chapter title
                    if para_stripped and not any(para_stripped == pattern for pattern in title_patterns):
                        filtered_paragraphs.append(para)
                
                result = '\n\n'.join(filtered_paragraphs)
            
            # If we got very little content, try a more aggressive approach
            if len(result.strip()) < 100:
                return self._extract_text_content_aggressive(html_content, chapter_title)
            
            return result
            
        except Exception as e:
            # Fallback to regex-based extraction if BeautifulSoup fails
            return self._extract_text_content_fallback(html_content, chapter_title)
    
    def _extract_text_content_aggressive(self, html_content, chapter_title=None):
        """More aggressive text extraction for complex EPUB content"""
        # Remove all style and script content first
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove CSS comments
        html_content = re.sub(r'/\*.*?\*/', '', html_content, flags=re.DOTALL)
        
        # Remove the epub-content wrapper div if present
        if '<div class="epub-content">' in html_content:
            start = html_content.find('<div class="epub-content">') + len('<div class="epub-content">')
            end = html_content.find('</div>', start)
            if end != -1:
                html_content = html_content[start:end].strip()
        
        # Remove all HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Handle HTML entities
        html_content = html_content.replace('&nbsp;', ' ')
        html_content = html_content.replace('&amp;', '&')
        html_content = html_content.replace('&lt;', '<')
        html_content = html_content.replace('&gt;', '>')
        html_content = html_content.replace('&quot;', '"')
        html_content = html_content.replace('&#39;', "'")
        html_content = html_content.replace('&ldquo;', '"')
        html_content = html_content.replace('&rdquo;', '"')
        html_content = html_content.replace('&lsquo;', "'")
        html_content = html_content.replace('&rsquo;', "'")
        html_content = html_content.replace('&mdash;', '—')
        html_content = html_content.replace('&ndash;', '–')
        
        # Clean up whitespace and split into lines
        lines = html_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Only include lines with substantial content
            if line and len(line) > 5 and re.search(r'[a-zA-Z]', line):
                # Clean up whitespace
                line = re.sub(r'\s+', ' ', line).strip()
                cleaned_lines.append(line)
        
        result = '\n\n'.join(cleaned_lines)
        
        # Remove chapter title from content if provided to avoid duplication
        if chapter_title and result:
            # Try to remove the chapter title from the beginning of the content
            title_patterns = [
                chapter_title,
                chapter_title.strip(),
                chapter_title.upper(),
                chapter_title.lower(),
                chapter_title.title(),
            ]
            
            for pattern in title_patterns:
                if result.startswith(pattern):
                    result = result[len(pattern):].strip()
                    break
            
            # Also try to remove it if it appears as a separate paragraph
            paragraphs = result.split('\n\n')
            filtered_paragraphs = []
            for para in paragraphs:
                para_stripped = para.strip()
                # Skip paragraphs that match the chapter title
                if para_stripped and not any(para_stripped == pattern for pattern in title_patterns):
                    filtered_paragraphs.append(para)
            
            result = '\n\n'.join(filtered_paragraphs)
        
        return result
    
    def _extract_text_content_fallback(self, html_content, chapter_title=None):
        """Fallback text extraction using regex"""
        # Remove all style and script tags
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove the epub-content wrapper div if present
        if '<div class="epub-content">' in html_content:
            start = html_content.find('<div class="epub-content">') + len('<div class="epub-content">')
            end = html_content.find('</div>', start)
            if end != -1:
                html_content = html_content[start:end].strip()
        
        # Remove all HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Handle HTML entities
        html_content = html_content.replace('&nbsp;', ' ')
        html_content = html_content.replace('&amp;', '&')
        html_content = html_content.replace('&lt;', '<')
        html_content = html_content.replace('&gt;', '>')
        html_content = html_content.replace('&quot;', '"')
        html_content = html_content.replace('&#39;', "'")
        html_content = html_content.replace('&ldquo;', '"')
        html_content = html_content.replace('&rdquo;', '"')
        html_content = html_content.replace('&lsquo;', "'")
        html_content = html_content.replace('&rsquo;', "'")
        html_content = html_content.replace('&mdash;', '—')
        html_content = html_content.replace('&ndash;', '–')
        
        # Clean up whitespace
        lines = html_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 5 and re.search(r'[a-zA-Z]', line):
                line = re.sub(r'\s+', ' ', line).strip()
                cleaned_lines.append(line)
        
        result = '\n\n'.join(cleaned_lines)
        
        # Remove chapter title from content if provided to avoid duplication
        if chapter_title and result:
            # Try to remove the chapter title from the beginning of the content
            title_patterns = [
                chapter_title,
                chapter_title.strip(),
                chapter_title.upper(),
                chapter_title.lower(),
                chapter_title.title(),
            ]
            
            for pattern in title_patterns:
                if result.startswith(pattern):
                    result = result[len(pattern):].strip()
                    break
            
            # Also try to remove it if it appears as a separate paragraph
            paragraphs = result.split('\n\n')
            filtered_paragraphs = []
            for para in paragraphs:
                para_stripped = para.strip()
                # Skip paragraphs that match the chapter title
                if para_stripped and not any(para_stripped == pattern for pattern in title_patterns):
                    filtered_paragraphs.append(para)
            
            result = '\n\n'.join(filtered_paragraphs)
        
        return result
    
    def _clean_text(self, text):
        """Clean and format text for PDF"""
        # Remove any remaining HTML tags that might have slipped through
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Handle any remaining HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&ldquo;', '"')
        text = text.replace('&rdquo;', '"')
        text = text.replace('&lsquo;', "'")
        text = text.replace('&rsquo;', "'")
        text = text.replace('&mdash;', '—')
        text = text.replace('&ndash;', '–')
        
        # Remove any CSS-like content that might remain
        text = re.sub(r'\{[^}]*\}', '', text)  # Remove CSS rules
        text = re.sub(r'@[^{]*\{[^}]*\}', '', text)  # Remove CSS at-rules
        
        # Clean up any remaining whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _add_page_number(self, canvas, doc):
        """Add page number to the bottom of each page"""
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        
        # Get page dimensions
        page_width, page_height = doc.pagesize
        
        # Position text at bottom center of page
        canvas.saveState()
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.black)
        
        # Calculate text width for centering
        text_width = canvas.stringWidth(text, 'Helvetica', 10)
        x = (page_width - text_width) / 2
        y = 0.5 * inch  # Position above bottom margin
        
        canvas.drawString(x, y, text)
        canvas.restoreState()
    

    
    def get_pdf_response(self, format_type='standard', quality='standard'):
        """Generate PDF and return HTTP response for download"""
        try:
            pdf_path = self.generate_pdf(format_type, quality)
            
            # Read the PDF file
            with open(pdf_path, 'rb') as pdf_file:
                response = HttpResponse(pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
                response['Content-Length'] = os.path.getsize(pdf_path)
            
            return response
            
        except Exception as e:
            raise Exception(f"Error generating PDF: {str(e)}")
