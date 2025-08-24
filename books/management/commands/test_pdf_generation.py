from django.core.management.base import BaseCommand
from books.models import Book
from books.pdf_generator import PDFGenerator
import os

class Command(BaseCommand):
    help = 'Test PDF generation for books'

    def add_arguments(self, parser):
        parser.add_argument(
            '--book-id',
            type=int,
            help='Specific book ID to test',
        )
        parser.add_argument(
            '--format',
            type=str,
            default='standard',
            choices=['standard', 'mobile'],
            help='PDF format to test',
        )
        parser.add_argument(
            '--quality',
            type=str,
            default='standard',
            choices=['standard', 'high', 'print'],
            help='PDF quality to test',
        )

    def handle(self, *args, **options):
        book_id = options['book_id']
        format_type = options['format']
        quality = options['quality']

        if book_id:
            try:
                book = Book.objects.get(id=book_id)
                self.test_book_pdf(book, format_type, quality)
            except Book.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Book with ID {book_id} not found')
                )
        else:
            books = Book.objects.all()
            if not books.exists():
                self.stdout.write(
                    self.style.WARNING('No books found in database')
                )
                return

            self.stdout.write(f'Testing PDF generation for {books.count()} books...')
            for book in books:
                self.test_book_pdf(book, format_type, quality)

    def test_book_pdf(self, book, format_type, quality):
        self.stdout.write(f'\nTesting PDF generation for: {book.title}')
        
        try:
            # Check if book has chapters
            if not book.chapters.exists():
                self.stdout.write(
                    self.style.WARNING(f'  - No chapters found for {book.title}')
                )
                return

            # Generate PDF
            pdf_generator = PDFGenerator(book)
            pdf_path = pdf_generator.generate_pdf(format_type, quality)
            
            # Check if file was created
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                file_size_mb = file_size / (1024 * 1024)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ PDF generated successfully: {os.path.basename(pdf_path)} '
                        f'({file_size_mb:.2f} MB)'
                    )
                )
                self.stdout.write(f'  - Format: {format_type}, Quality: {quality}')
                self.stdout.write(f'  - Chapters: {book.chapters.count()}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ PDF file not created: {pdf_path}')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Error generating PDF: {str(e)}')
            )
