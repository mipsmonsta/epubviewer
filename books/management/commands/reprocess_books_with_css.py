from django.core.management.base import BaseCommand
from books.models import Book, Chapter
from books.epub_parser import extract_css_styles, process_chapter_content, update_image_references, update_internal_links
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os

class Command(BaseCommand):
    help = 'Reprocess existing books to apply CSS styling'

    def add_arguments(self, parser):
        parser.add_argument(
            '--book-id',
            type=int,
            help='Reprocess only a specific book by ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing even if CSS already exists',
        )

    def handle(self, *args, **options):
        book_id = options.get('book_id')
        force = options.get('force', False)
        
        if book_id:
            books = Book.objects.filter(id=book_id)
            if not books.exists():
                self.stdout.write(
                    self.style.ERROR(f'Book with ID {book_id} not found')
                )
                return
        else:
            books = Book.objects.all()
        
        self.stdout.write(f'Found {books.count()} book(s) to process')
        
        for book in books:
            self.stdout.write(f'\nProcessing book: "{book.title}" (ID: {book.id})')
            
            try:
                # Check if CSS already exists
                css_dir = f'media/book_css/{book.id}'
                css_file = f'{css_dir}/styles.css'
                
                if not force and os.path.exists(css_file):
                    self.stdout.write(
                        self.style.WARNING(f'CSS already exists for book {book.id}. Use --force to reprocess.')
                    )
                    # Still reprocess chapters even if CSS exists
                    self.reprocess_chapters(book)
                    continue
                
                # Load EPUB
                epub_book = epub.read_epub(book.file.path)
                
                # Extract CSS
                css_styles = extract_css_styles(epub_book, book.id)
                self.stdout.write(f'Extracted {len(css_styles)} characters of CSS')
                
                # Reprocess all chapters with CSS
                self.reprocess_chapters(book, css_styles)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully reprocessed book: {book.title}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing book {book.title}: {str(e)}')
                )
    
    def reprocess_chapters(self, book, css_styles=None):
        """Reprocess all chapters for a book with CSS styling"""
        chapters = book.chapters.all()
        self.stdout.write(f'Reprocessing {chapters.count()} chapters...')
        
        # If CSS styles not provided, try to load from file
        if css_styles is None:
            css_file = f'media/book_css/{book.id}/styles.css'
            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_styles = f.read()
            else:
                css_styles = ''
        
        for chapter in chapters:
            try:
                # Parse existing chapter content to get the original HTML
                soup = BeautifulSoup(chapter.content, 'html.parser')
                
                # If content already has epub-content wrapper, extract the original content
                epub_content_div = soup.find('div', class_='epub-content')
                if epub_content_div:
                    # Remove style tag and get the inner content
                    style_tag = epub_content_div.find('style')
                    if style_tag:
                        style_tag.decompose()
                    # Get the content without the wrapper
                    inner_content = ''.join(str(child) for child in epub_content_div.children)
                    soup = BeautifulSoup(inner_content, 'html.parser')
                
                # Apply new CSS processing
                new_content = process_chapter_content(soup, css_styles)
                
                # Update chapter
                chapter.content = new_content
                chapter.save()
                
                self.stdout.write(f'  ✓ Updated chapter: {chapter.title}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  ✗ Error updating chapter {chapter.title}: {str(e)}')
                )
        
        self.stdout.write(f'Finished reprocessing chapters for: {book.title}')

