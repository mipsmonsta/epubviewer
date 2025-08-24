# EPUB Viewer

A Django-based web application for viewing EPUB files. Upload your EPUB books and read them in a clean, responsive web interface.

## Features

- **EPUB Upload**: Upload EPUB files with automatic parsing
- **Library Management**: View all your uploaded books
- **Chapter Navigation**: Easy navigation between chapters
- **Reading Progress**: Track your reading progress
- **PDF Generation**: Convert EPUB books to PDF with multiple format options
- **Responsive Design**: Works on desktop and mobile devices
- **Clean Interface**: Modern, distraction-free reading experience

## Technology Stack

- **Backend**: Django 5.2.5
- **EPUB Processing**: ebooklib 0.19
- **HTML Parsing**: BeautifulSoup4 4.13.4
- **XML Processing**: lxml 6.0.0
- **Image Processing**: Pillow 11.3.0
- **PDF Generation**: WeasyPrint
- **Frontend**: Bootstrap 5.3.0, Font Awesome 6.0.0

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd epubviewer
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - Windows:
     ```bash
     venv\Scripts\Activate.ps1
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

7. **Open your browser** and go to `http://127.0.0.1:8000/`

## Usage

### Uploading EPUB Files

1. Click the "Upload EPUB" button in the navigation
2. Select an EPUB file (maximum 50MB)
3. The system will automatically:
   - Extract metadata (title, author)
   - Parse chapters
   - Extract cover image (if available)
   - Store the file securely

### Reading Books

1. Go to the Library page to see all your books
2. Click "Read" on any book to open it
3. Select a chapter to start reading
4. Use the navigation buttons or arrow keys to move between chapters
5. Your reading progress is automatically saved

### Features

- **Keyboard Navigation**: Use left/right arrow keys to navigate chapters
- **Progress Tracking**: Visual progress bar shows reading progress
- **Chapter Dropdown**: Quick access to any chapter
- **Responsive Design**: Optimized for all screen sizes

### PDF Generation

The EPUB Viewer now supports converting books to PDF format with multiple options:

1. **Format Options**:
   - **Standard**: A4 page size, optimized for desktop and tablet viewing
   - **Mobile**: Narrow page width with larger fonts, optimized for smartphone reading

2. **Quality Options**:
   - **Standard Quality**: Fast generation, smaller file size
   - **High Quality**: Better typography, recommended for most uses
   - **Print Quality**: Maximum quality for printing

3. **How to Generate PDFs**:
   - From the Library page: Click the "PDF" button on any book card
   - From the Reader page: Click the "PDF" button in the navigation
   - From any Chapter page: Click the "PDF" button in the navigation
   - Select your preferred format and quality options
   - Click "Generate & Download PDF"

4. **PDF Features**:
   - Complete book content with all chapters
   - Table of contents with page numbers
   - Title page with book metadata
   - Proper page numbering
   - Optimized typography and layout
   - Image support (if present in EPUB)

## Project Structure

```
epubviewer/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── epubviewer/              # Main project settings
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL configuration
│   └── wsgi.py              # WSGI configuration
├── books/                   # Main app
│   ├── models.py            # Database models
│   ├── views.py             # View logic
│   ├── urls.py              # App URL patterns
│   ├── forms.py             # Form definitions
│   ├── epub_parser.py       # EPUB processing logic
│   ├── pdf_generator.py     # PDF generation logic
│   └── templates/           # HTML templates
│       └── books/
│           ├── base.html    # Base template
│           ├── library.html # Library page
│           ├── upload.html  # Upload page
│           ├── reader.html  # Book reader
│           ├── chapter.html # Chapter view
│           └── pdf_options.html # PDF generation options
├── media/                   # Uploaded files
│   ├── epubs/              # EPUB files
│   └── covers/             # Cover images
└── static/                 # Static files (CSS, JS)
```

## Models

### Book
- `title`: Book title (extracted from EPUB metadata)
- `author`: Book author (extracted from EPUB metadata)
- `file`: EPUB file storage
- `cover_image`: Cover image (extracted from EPUB)
- `uploaded_at`: Upload timestamp
- `last_position`: Reading progress tracking

### Chapter
- `book`: Foreign key to Book
- `title`: Chapter title
- `content`: Chapter HTML content
- `order`: Chapter order in the book

## API Endpoints

- `GET /`: Library page
- `GET /upload/`: Upload page
- `POST /upload/`: Upload EPUB file
- `GET /book/<id>/`: Book reader page
- `GET /book/<book_id>/chapter/<chapter_id>/`: Chapter view
- `POST /book/<book_id>/progress/`: Update reading progress
- `GET /book/<book_id>/pdf/`: PDF generation options page
- `GET /book/<book_id>/pdf/generate/`: Generate and download PDF

## Development

### Adding New Features

1. **Models**: Add new fields to `books/models.py`
2. **Views**: Create new views in `books/views.py`
3. **Templates**: Add new templates in `books/templates/books/`
4. **URLs**: Update `books/urls.py` with new routes

### Running Tests

```bash
python manage.py test
```

### Testing PDF Generation

```bash
# Test PDF generation for all books
python manage.py test_pdf_generation

# Test PDF generation for a specific book
python manage.py test_pdf_generation --book-id 1

# Test with specific format and quality
python manage.py test_pdf_generation --format mobile --quality high
```

### Database Reset

```bash
python manage.py flush
```

## Deployment

For production deployment:

1. Set `DEBUG = False` in `settings.py`
2. Configure a production database (PostgreSQL recommended)
3. Set up static file serving
4. Configure media file storage
5. Set up proper security settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on the GitHub repository.
