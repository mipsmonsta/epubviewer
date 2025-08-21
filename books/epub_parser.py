import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urljoin, urlparse
from .models import Book, Chapter

def parse_epub(book_instance):
    """Parse EPUB file and create chapters"""
    try:
        epub_book = epub.read_epub(book_instance.file.path)
        
        # Extract metadata
        title_meta = epub_book.get_metadata('DC', 'title')
        author_meta = epub_book.get_metadata('DC', 'creator')
        
        if title_meta:
            book_instance.title = title_meta[0][0]
        else:
            book_instance.title = os.path.splitext(os.path.basename(book_instance.file.name))[0]
        
        if author_meta:
            book_instance.author = author_meta[0][0]
        else:
            book_instance.author = "Unknown"
        
        book_instance.save()
        
        # Clear existing chapters
        book_instance.chapters.all().delete()
        
        # Create images directory for this book
        book_images_dir = f'media/book_images/{book_instance.id}'
        os.makedirs(book_images_dir, exist_ok=True)
        
        # Extract and store images
        image_map = extract_images(epub_book, book_instance.id)
        
        # Extract CSS styles
        css_styles = extract_css_styles(epub_book, book_instance.id)
        
        # Build a mapping of internal references to chapter IDs
        internal_refs = {}
        chapter_order = 0
        for item in epub_book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Skip cover pages and other non-chapter content
                item_name = item.get_name().lower()
                print(f"Processing document: {item_name}")
                if any(skip in item_name for skip in ['cover', 'title', 'copyright', 'toc']):
                    print(f"Skipping {item_name} - appears to be non-chapter content")
                    continue
                
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                
                # Get chapter title
                title = "Chapter"
                if soup.title:
                    title = soup.title.string
                elif soup.find('h1'):
                    title = soup.find('h1').get_text()
                elif soup.find('h2'):
                    title = soup.find('h2').get_text()
                else:
                    title = f"Chapter {chapter_order + 1}"
                
                # Skip if this appears to be a non-content page
                if len(title.strip()) < 3 or title.lower() in ['cover', 'title page', 'copyright']:
                    continue
                
                # Update image references in content
                update_image_references(soup, image_map, book_instance.id)
                
                # Update internal links to point to Django chapter URLs
                update_internal_links(soup, book_instance.id, internal_refs)
                
                # Process chapter content with CSS styles
                content = process_chapter_content(soup, css_styles)
                
                # Only create chapter if there's meaningful content
                if len(content.strip()) > 100:  # Minimum content length
                    chapter = Chapter.objects.create(
                        book=book_instance,
                        title=title,
                        content=content,
                        order=chapter_order
                    )
                    
                    # Store mapping for internal references
                    item_name = item.get_name()
                    internal_refs[item_name] = chapter.id
                    internal_refs[os.path.basename(item_name)] = chapter.id
                    
                    chapter_order += 1
        
        return True
    except Exception as e:
        print(f"Error parsing EPUB: {e}")
        return False

def extract_images(epub_book, book_id):
    """Extract images from EPUB and return a mapping of original paths to new paths"""
    image_map = {}
    book_images_dir = f'media/book_images/{book_id}'
    
    for item in epub_book.get_items():
        if item.get_type() == ebooklib.ITEM_IMAGE:
            try:
                # Get the original path
                original_path = item.get_name()
                
                # Create a safe filename
                filename = os.path.basename(original_path)
                safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
                
                # Save the image
                new_path = f'{book_images_dir}/{safe_filename}'
                with open(new_path, 'wb') as f:
                    f.write(item.get_content())
                
                # Map original path to new path
                image_map[original_path] = f'/media/book_images/{book_id}/{safe_filename}'
                
            except Exception as e:
                print(f"Error extracting image {original_path}: {e}")
    
    return image_map

def update_image_references(soup, image_map, book_id):
    """Update image src attributes in the HTML content"""
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # Normalize the path
            src = src.strip()
            
            # Handle relative paths
            if src.startswith('../'):
                src = src[3:]  # Remove '../'
            elif src.startswith('./'):
                src = src[2:]  # Remove './'
            
            # Remove any URL parameters
            if '?' in src:
                src = src.split('?')[0]
            
            # Check if we have this image in our map
            if src in image_map:
                img['src'] = image_map[src]
            else:
                # Try to find the image with different path variations
                found = False
                for original_path, new_path in image_map.items():
                    # Try exact match
                    if src == original_path:
                        img['src'] = new_path
                        found = True
                        break
                    # Try basename match
                    elif os.path.basename(src) == os.path.basename(original_path):
                        img['src'] = new_path
                        found = True
                        break
                    # Try partial path match
                    elif src in original_path or original_path.endswith(src):
                        img['src'] = new_path
                        found = True
                        break
                
                if not found:
                    print(f"Could not find image: {src}")
                    # Remove the image if we can't find it
                    img.decompose()

def update_internal_links(soup, book_id, internal_refs):
    """Update internal links in the HTML content to point to Django chapter URLs"""
    # Find all links
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            # Handle internal links (links to other parts of the EPUB)
            if href.startswith('#'):
                # Anchor links - remove them but keep text
                link_text = link.get_text()
                link.replace_with(link_text)
            elif href.endswith('.xhtml') or href.endswith('.html'):
                # Internal file links - try to map to chapter
                target_file = href.split('#')[0] if '#' in href else href
                if target_file in internal_refs:
                    # Found matching chapter, update link
                    chapter_id = internal_refs[target_file]
                    link['href'] = f'/book/{book_id}/chapter/{chapter_id}/'
                else:
                    # No matching chapter, remove link but keep text
                    link_text = link.get_text()
                    link.replace_with(link_text)
            elif href.startswith('http'):
                # External links - keep them as is
                continue
            else:
                # Other internal links - try to find match
                if href in internal_refs:
                    chapter_id = internal_refs[href]
                    link['href'] = f'/book/{book_id}/chapter/{chapter_id}/'
                else:
                    # No match found, remove link but keep text
                    link_text = link.get_text()
                    link.replace_with(link_text)

def extract_css_styles(epub_book, book_id):
    """Extract CSS styles from EPUB and return combined CSS"""
    css_content = []
    
    # Create CSS directory for this book
    css_dir = f'media/book_css/{book_id}'
    os.makedirs(css_dir, exist_ok=True)
    
    for item in epub_book.get_items():
        if item.get_type() == ebooklib.ITEM_STYLE:
            try:
                css_text = item.get_content().decode('utf-8')
                # Sanitize CSS to prevent conflicts
                css_text = sanitize_css(css_text)
                css_content.append(css_text)
                print(f"Extracted CSS from: {item.get_name()}")
            except Exception as e:
                print(f"Error extracting CSS from {item.get_name()}: {e}")
    
    # Combine all CSS
    combined_css = '\n'.join(css_content)
    
    # Save combined CSS file
    if combined_css:
        css_file_path = f'{css_dir}/styles.css'
        with open(css_file_path, 'w', encoding='utf-8') as f:
            f.write(combined_css)
        print(f"Saved combined CSS to: {css_file_path}")
    
    return combined_css

def sanitize_css(css_text):
    """Sanitize CSS to prevent conflicts with application styles"""
    # Remove any potentially conflicting styles
    css_text = re.sub(r'body\s*\{[^}]*\}', '', css_text, flags=re.IGNORECASE)
    css_text = re.sub(r'html\s*\{[^}]*\}', '', css_text, flags=re.IGNORECASE)
    css_text = re.sub(r'\.container\s*\{[^}]*\}', '', css_text, flags=re.IGNORECASE)
    css_text = re.sub(r'\.navbar\s*\{[^}]*\}', '', css_text, flags=re.IGNORECASE)
    
    # Add book-specific prefix to prevent conflicts
    css_text = re.sub(r'([.#][a-zA-Z][a-zA-Z0-9_-]*)\s*{', r'.epub-content \1 {', css_text)
    
    # Also prefix general element selectors
    css_text = re.sub(r'^([a-zA-Z][a-zA-Z0-9]*)\s*{', r'.epub-content \1 {', css_text, flags=re.MULTILINE)
    
    return css_text

def process_chapter_content(soup, css_styles):
    """Process chapter content and include CSS styles"""
    # Get the body content
    body_content = str(soup.body) if soup.body else str(soup)
    
    # Create a new HTML structure with CSS
    html_content = f"""
    <div class="epub-content">
        <style>
        /* EPUB Original Styles */
        {css_styles}
        
        /* Additional styling for better integration */
        .epub-content {{
            font-family: inherit;
            line-height: 1.6;
        }}
        
        .epub-content p {{
            margin-bottom: 1rem;
        }}
        
        .epub-content img {{
            max-width: 100%;
            height: auto;
            margin: 1rem 0;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .epub-content h1, .epub-content h2, .epub-content h3, 
        .epub-content h4, .epub-content h5, .epub-content h6 {{
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        
        .epub-content blockquote {{
            border-left: 4px solid #007bff;
            padding-left: 1rem;
            margin: 1rem 0;
            font-style: italic;
        }}
        
        .epub-content code {{
            background-color: #f8f9fa;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: monospace;
        }}
        
        .epub-content pre {{
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
        }}
        </style>
        {body_content}
    </div>
    """
    return html_content

def extract_cover_image(book_instance):
    """Extract cover image from EPUB if available"""
    try:
        epub_book = epub.read_epub(book_instance.file.path)
        
        # Create covers directory if it doesn't exist
        covers_dir = 'media/covers'
        os.makedirs(covers_dir, exist_ok=True)
        
        # Look for cover image
        for item in epub_book.get_items():
            if item.get_type() == ebooklib.ITEM_COVER:
                # Save cover image
                cover_path = f'covers/{book_instance.id}_cover.jpg'
                full_path = f'media/{cover_path}'
                with open(full_path, 'wb') as f:
                    f.write(item.get_content())
                book_instance.cover_image = cover_path
                book_instance.save()
                print(f"Cover image extracted: {cover_path}")
                break
        else:
            print("No cover image found in EPUB")
    except Exception as e:
        print(f"Error extracting cover: {e}")
