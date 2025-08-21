from django.db import models
import os

# Create your models here.

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to='epubs/')
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_position = models.IntegerField(default=0)  # Track reading progress
    last_chapter = models.ForeignKey('Chapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_read_in')
    
    def __str__(self):
        return self.title
    
    def filename(self):
        return os.path.basename(self.file.name)
    
    def delete(self, *args, **kwargs):
        # Delete the file from filesystem when the model is deleted
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.cover_image:
            if os.path.isfile(self.cover_image.path):
                os.remove(self.cover_image.path)
        
        # Delete extracted images directory
        book_images_dir = f'media/book_images/{self.id}'
        if os.path.exists(book_images_dir):
            import shutil
            shutil.rmtree(book_images_dir)
        
        # Delete extracted CSS directory
        book_css_dir = f'media/book_css/{self.id}'
        if os.path.exists(book_css_dir):
            import shutil
            shutil.rmtree(book_css_dir)
        
        super().delete(*args, **kwargs)
    
    class Meta:
        ordering = ['-uploaded_at']

class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.IntegerField()
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.book.title} - {self.title}"
