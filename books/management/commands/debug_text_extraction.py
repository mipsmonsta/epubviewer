from django.core.management.base import BaseCommand
from books.models import Book, Chapter
from books.pdf_generator import PDFGenerator

class Command(BaseCommand):
    help = 'Debug text extraction from EPUB content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--book-id',
            type=int,
            required=True,
            help='Book ID to debug',
        )
        parser.add_argument(
            '--chapter-id',
            type=int,
            help='Specific chapter ID to debug (optional)',
        )

    def handle(self, *args, **options):
        book_id = options['book_id']
        chapter_id = options['chapter_id']

        try:
            book = Book.objects.get(id=book_id)
            self.stdout.write(f'Debugging text extraction for: {book.title}')
            
            if chapter_id:
                # Debug specific chapter
                chapter = Chapter.objects.get(id=chapter_id, book=book)
                self.debug_chapter(chapter)
            else:
                # Debug first few chapters
                chapters = book.chapters.all().order_by('order')[:3]
                for chapter in chapters:
                    self.debug_chapter(chapter)
                    self.stdout.write('-' * 80)
                    
        except Book.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Book with ID {book_id} not found')
            )
        except Chapter.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Chapter with ID {chapter_id} not found')
            )

    def debug_chapter(self, chapter):
        self.stdout.write(f'\nChapter: {chapter.title}')
        self.stdout.write('=' * 50)
        
        # Show original content length
        self.stdout.write(f'Original content length: {len(chapter.content)} characters')
        
        # Show first 200 characters of original content
        self.stdout.write('\nOriginal content (first 200 chars):')
        self.stdout.write('-' * 30)
        self.stdout.write(chapter.content[:200] + '...' if len(chapter.content) > 200 else chapter.content)
        
        # Create PDF generator instance to use its text extraction
        pdf_generator = PDFGenerator(chapter.book)
        
        # Extract cleaned text
        cleaned_text = pdf_generator._extract_text_content(chapter.content)
        
        self.stdout.write(f'\nCleaned text length: {len(cleaned_text)} characters')
        
        # Show first 500 characters of cleaned text
        self.stdout.write('\nCleaned text (first 500 chars):')
        self.stdout.write('-' * 30)
        self.stdout.write(cleaned_text[:500] + '...' if len(cleaned_text) > 500 else cleaned_text)
        
        # Show paragraph count
        paragraphs = cleaned_text.split('\n\n')
        self.stdout.write(f'\nParagraph count: {len(paragraphs)}')
        
        # Show first few paragraphs
        self.stdout.write('\nFirst 3 paragraphs:')
        self.stdout.write('-' * 30)
        for i, para in enumerate(paragraphs[:3]):
            if para.strip():
                self.stdout.write(f'Paragraph {i+1}: {para.strip()[:100]}...' if len(para) > 100 else f'Paragraph {i+1}: {para.strip()}')
                self.stdout.write('')
