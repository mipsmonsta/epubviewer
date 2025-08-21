from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .models import Book, Chapter
from .forms import BookUploadForm
from .epub_parser import parse_epub, extract_cover_image

class LibraryView(ListView):
    model = Book
    template_name = 'books/library.html'
    context_object_name = 'books'
    ordering = ['-uploaded_at']

class BookReaderView(DetailView):
    model = Book
    template_name = 'books/reader.html'
    context_object_name = 'book'
    
    def get(self, request, *args, **kwargs):
        book = self.get_object()
        
        # If user has a last read chapter, redirect to it
        if book.last_chapter:
            try:
                # Verify the chapter still exists
                chapter = Chapter.objects.get(id=book.last_chapter.id, book=book)
                return redirect('books:chapter', book_id=book.id, chapter_id=chapter.id)
            except Chapter.DoesNotExist:
                # Chapter was deleted, clear the reference
                book.last_chapter = None
                book.save()
        
        # If no last chapter or chapter doesn't exist, show the first chapter
        first_chapter = book.chapters.first()
        if first_chapter:
            return redirect('books:chapter', book_id=book.id, chapter_id=first_chapter.id)
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['chapters'] = self.object.chapters.all()
        return context

class BookUploadView(CreateView):
    model = Book
    form_class = BookUploadForm
    template_name = 'books/upload.html'
    success_url = reverse_lazy('books:library')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Parse EPUB and create chapters
        if parse_epub(form.instance):
            # Try to extract cover image
            extract_cover_image(form.instance)
            messages.success(self.request, f'Successfully uploaded and parsed "{form.instance.title}"')
        else:
            messages.error(self.request, 'Error parsing EPUB file. Please check if it\'s a valid EPUB.')
            form.instance.delete()
            return redirect('books:upload')
        
        return response

class BookDeleteView(DeleteView):
    model = Book
    template_name = 'books/book_confirm_delete.html'
    success_url = reverse_lazy('books:library')
    
    def delete(self, request, *args, **kwargs):
        book = self.get_object()
        title = book.title
        messages.success(request, f'Successfully deleted "{title}"')
        return super().delete(request, *args, **kwargs)

def chapter_view(request, book_id, chapter_id):
    """View for individual chapters"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(Chapter, id=chapter_id, book=book)
    
    # Update the last read chapter when user visits a chapter
    if book.last_chapter != chapter:
        book.last_chapter = chapter
        book.last_position = 0  # Reset position for new chapter
        book.save()
        print(f"Updated last read chapter for '{book.title}': '{chapter.title}'")
    
    # Get previous and next chapters
    prev_chapter = Chapter.objects.filter(book=book, order__lt=chapter.order).order_by('-order').first()
    next_chapter = Chapter.objects.filter(book=book, order__gt=chapter.order).order_by('order').first()
    
    # Check if this is the last read chapter to restore scroll position
    restore_position = False
    if book.last_chapter and book.last_chapter.id == chapter.id:
        restore_position = True
    
    context = {
        'book': book,
        'chapter': chapter,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'chapters': book.chapters.all(),
        'restore_position': restore_position,
        'last_position': book.last_position if restore_position else 0,
    }
    
    return render(request, 'books/chapter.html', context)

def update_progress(request, book_id):
    """Update reading progress via AJAX"""
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        position = request.POST.get('position', 0)
        chapter_id = request.POST.get('chapter_id')
        
        try:
            book.last_position = int(position)
            if chapter_id:
                chapter = get_object_or_404(Chapter, id=chapter_id, book=book)
                book.last_chapter = chapter
                print(f"Updated progress for book '{book.title}': Chapter '{chapter.title}', Position {position}%")
            book.save()
            return JsonResponse({'status': 'success', 'message': f'Progress updated: {position}% in chapter {chapter.title if chapter_id else "unknown"}'})
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid position'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def debug_progress(request):
    """Debug view to check reading progress"""
    books = Book.objects.all()
    debug_info = []
    
    for book in books:
        debug_info.append({
            'title': book.title,
            'last_chapter': book.last_chapter.title if book.last_chapter else 'None',
            'last_position': book.last_position,
            'total_chapters': book.chapters.count()
        })
    
    response = "Reading Progress Debug Info:\n\n"
    for info in debug_info:
        response += f"Book: {info['title']}\n"
        response += f"  Last Chapter: {info['last_chapter']}\n"
        response += f"  Position: {info['last_position']}%\n"
        response += f"  Total Chapters: {info['total_chapters']}\n\n"
    
    return HttpResponse(response, content_type='text/plain')
