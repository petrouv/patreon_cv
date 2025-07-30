"""Converts raw Patreon API responses for posts into standalone HTML files.

This script processes JSON files containing Patreon post data, extracts relevant
information such as title, content, author, and dates, and generates a
well-formatted HTML file for each post using a Jinja2 template. It also
replaces remote image URLs with local paths.

Usage:
    python main.py <path_to_posts>

Arguments:
    path_to_posts: A path to a single post directory or a directory 
                   containing multiple post directories.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from jinja2 import Environment, FileSystemLoader


def find_post_files(root_dir):
    """Finds all 'post-api.json' files within a directory.

    Args:
        root_dir (str): The path to the directory to search.

    Yields:
        str: The full path to each found 'post-api.json' file.
    """
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename == 'post-api.json':
                yield os.path.join(dirpath, filename)

def get_author_info(data):
    """Extracts author information from the post data.

    Args:
        data (dict): The parsed JSON data of the post.

    Returns:
        dict: A dictionary containing the author's name and profile URL.
    """
    user_id = data['data']['relationships']['user']['data']['id']
    for item in data['included']:
        if item['type'] == 'user' and item['id'] == user_id:
            attributes = item['attributes']
            return {
                'name': attributes.get('vanity', 'Unknown Author'),
                'url': attributes.get('url', '#')
            }
    return {'name': 'Unknown Author', 'url': '#'}

def local_image_path_replace(content, json_path):
    """Replaces remote image URLs in post content with local paths.

    Args:
        content (str): The HTML content of the post.
        json_path (str): The path to the post's JSON file.

    Returns:
        str: The updated HTML content with local image paths.
    """
    
    def replace_func(match):
        img_tag = match.group(0)
        src_match = re.search(r'src="([^"]+)"', img_tag)
        if not src_match:
            return img_tag

        original_src = src_match.group(1)
        
        # Extract the unique filename from the URL
        file_name_match = re.search(r'([a-f0-9]{32}|[a-f0-9-]{36})~mv2', original_src)
        if not file_name_match:
            # If not found, try another pattern that sometimes appears in the data
            file_name_match = re.search(r'd23bd2_([a-f0-9]{32})~mv2', original_src)
            if not file_name_match:
                return img_tag # If still not found, return as is
        
        unique_part = file_name_match.group(0)

        images_dir = os.path.join(os.path.dirname(os.path.dirname(json_path)), 'images')
        
        # Search for a file in the images folder that contains the unique part
        found_image = None
        if os.path.exists(images_dir):
            for img_file in os.listdir(images_dir):
                if unique_part in img_file:
                    found_image = img_file
                    break
        
        if found_image:
            local_path = os.path.join('..', 'images', found_image)
            return f'<div class="image-container"><a href="{local_path}" target="_blank" rel="noopener"><img src="{local_path}" alt="Image from post" loading="lazy"></a></div>'
        else:
            # If the local file is not found, keep the original src, but wrap it in a div
            return f'<div class="image-container"><img src="{original_src}" alt="Image from post (local not found)" loading="lazy"></div>'

    # Replace each img tag
    content = re.sub(r'<p><img[^>]+></p>', replace_func, content)
    
    # Clean up empty <p> tags that may have been left after replacement
    content = re.sub(r'<p>\s*</p>', '', content)

    return content


def create_html_from_json(json_path, template):
    """Creates an HTML file from a post's JSON data.

    Args:
        json_path (str): The path to the post's JSON file.
        template (jinja2.Template): The Jinja2 template to use for rendering.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    post_attributes = data['data']['attributes']
    
    # Convert content
    content = local_image_path_replace(post_attributes.get('content', ''), json_path)

    # Convert date formats
    published_at_iso = post_attributes.get('published_at', '')
    published_at_human = ''
    if published_at_iso:
        dt_obj = datetime.fromisoformat(published_at_iso.replace('Z', '+00:00'))
        published_at_human = dt_obj.strftime('%d.%m.%Y at %H:%M UTC')

    edited_at_iso = post_attributes.get('edited_at', '')
    edited_at_human = ''
    if edited_at_iso and edited_at_iso != published_at_iso:
        dt_obj = datetime.fromisoformat(edited_at_iso.replace('Z', '+00:00'))
        edited_at_human = dt_obj.strftime('%d.%m.%Y at %H:%M UTC')

    # Get file creation and modification times
    mod_time_ts = os.path.getmtime(json_path)
    try:
        # os.path.getctime() may return the metadata change time on Unix-like systems
        # and the creation time on Windows. For better reliability, use stat().st_birthtime on macOS/BSD
        birth_time_ts = os.stat(json_path).st_birthtime
    except AttributeError:
        # If st_birthtime is not available (e.g., on some Linux systems), use ctime
        birth_time_ts = os.path.getctime(json_path)

    # Choose the earliest date
    earliest_time_ts = min(mod_time_ts, birth_time_ts)
    earliest_time_dt = datetime.fromtimestamp(earliest_time_ts)
    saved_at_human = earliest_time_dt.strftime('%d.%m.%Y at %H:%M UTC')

    post_data = {
        'title': post_attributes.get('title', 'No Title'),
        'content': content,
        'published_at': published_at_iso,
        'published_at_human': published_at_human,
        'edited_at': edited_at_iso,
        'edited_at_human': edited_at_human,
        'author': get_author_info(data),
        'url': post_attributes.get('url', '#'),
        'saved_at': saved_at_human,
    }

    output_html = template.render(post=post_data)
    output_path = os.path.join(os.path.dirname(json_path), 'post.html')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_html)
    
    print(f"Successfully converted {json_path} to {output_path}")

def main():
    """Main function to run the conversion script."""
    start_time = time.time()
    parser = argparse.ArgumentParser(description='Convert Patreon API responses to HTML pages.')
    parser.add_argument('path', type=str, help='Path to a post directory or a directory containing multiple post directories.')
    args = parser.parse_args()

    input_path = args.path

    if not os.path.exists(input_path):
        print(f"Error: Path not found at '{input_path}'", file=sys.stderr)
        sys.exit(1)

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('post_template.html')

    json_files_to_process = []
    
    # Check if the path is a single post directory
    single_post_json = os.path.join(input_path, 'post_info', 'post-api.json')
    if os.path.isfile(single_post_json):
        json_files_to_process.append(single_post_json)
    # Otherwise, if it's a directory with multiple posts
    elif os.path.isdir(input_path):
        for json_file in find_post_files(input_path):
            json_files_to_process.append(json_file)

    if not json_files_to_process:
        print(f"No 'post-api.json' files found in '{input_path}'", file=sys.stderr)
        sys.exit(1)

    success_count = 0
    error_count = 0

    for json_file in json_files_to_process:
        try:
            create_html_from_json(json_file, template)
            success_count += 1
        except Exception as e:
            print(f"Error processing {json_file}: {e}", file=sys.stderr)
            error_count += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n--- Conversion Statistics ---")
    print(f"Successfully converted: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Total files processed: {len(json_files_to_process)}")
    print(f"Total duration: {duration:.2f} seconds")
    print("---------------------------\n")


if __name__ == '__main__':
    main()
