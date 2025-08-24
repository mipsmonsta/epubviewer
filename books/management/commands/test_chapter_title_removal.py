from django.core.management.base import BaseCommand
from books.models import Book, Chapter
from books.pdf_generator import PDFGenerator

class Command(BaseCommand):
    help = 'Test chapter title removal to avoid duplication in PDF generation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--book-id',
            type=int,
            required=True,
            help='Book ID to test',
        )

    def handle(self, *args, **options):
        book_id = options['book_id']

        try:
            book = Book.objects.get(id=book_id)
            self.stdout.write(f'Testing chapter title removal for: {book.title}')
            
            # Test first few chapters
            chapters = book.chapters.all().order_by('order')[:3]
            pdf_generator = PDFGenerator(book)
            
            for chapter in chapters:
                self.test_chapter_title_removal(chapter, pdf_generator)
                self.stdout.write('-' * 80)
                    
        except Book.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Book with ID {book_id} not found')
            )

    def test_chapter_title_removal(self, chapter, pdf_generator):
        self.stdout.write(f'\nChapter: {chapter.title}')
        self.stdout.write('=' * 50)
        
        # Test extraction without title removal
        content_without_removal = pdf_generator._extract_text_content(chapter.content)
        
        # Test extraction with title removal
        content_with_removal = pdf_generator._extract_text_content(chapter.content, chapter.title)
        
        self.stdout.write(f'\nContent length without title removal: {len(content_without_removal)}')
        self.stdout.write(f'Content length with title removal: {len(content_with_removal)}')
        
        # Show first 200 characters of each
        self.stdout.write('\nFirst 200 chars WITHOUT title removal:')
        self.stdout.write('-' * 40)
        self.stdout.write(content_without_removal[:200] + '...' if len(content_without_removal) > 200 else content_without_removal)
        
        self.stdout.write('\nFirst 200 chars WITH title removal:')
        self.stdout.write('-' * 40)
        self.stdout.write(content_with_removal[:200] + '...' if len(content_with_removal) > 200 else content_with_removal)
        
        # Check if the chapter title appears in the content
        title_in_content = chapter.title in content_without_removal
        title_in_removed = chapter.title in content_with_removal
        
        self.stdout.write(f'\nChapter title appears in content (without removal): {title_in_content}')
        self.stdout.write(f'Chapter title appears in content (with removal): {title_in_removed}')
        
        if title_in_content and not title_in_removed:
            self.stdout.write(self.style.SUCCESS('  ✓ Title removal working correctly'))
        elif not title_in_content:
            self.stdout.write(self.style.WARNING('  - No title found in original content'))
        else:
            self.stdout.write(self.style.ERROR('  ✗ Title still appears in content after removal'))
