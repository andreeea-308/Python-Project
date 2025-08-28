import os
from book_summaries import book_summaries_dict, book_metadata


def create_individual_book_files():
    """
    Creează fișiere individuale pentru fiecare carte conform cerințelor
    """
    # Creează directorul
    os.makedirs("book_files", exist_ok=True)

    for title, summary in book_summaries_dict.items():
        # Creează numele fișierului (înlocuiește spațiile și caracterele speciale)
        filename = f"book_files/{title.replace(' ', '_').replace(':', '').replace(',', '')}.txt"

        # Obține metadata
        metadata = book_metadata.get(title, {})

        # Creează conținutul fișierului conform cerințelor
        content = f"""## Title: {title}

A {metadata.get('genre', 'Unknown genre')} book by {metadata.get('author', 'Unknown author')}.

Target Audience: {metadata.get('target_audience', 'General')}

Main Themes: {', '.join(metadata.get('themes', []))}

Summary:
{summary}

Key Elements:
- Genre: {metadata.get('genre', 'Unknown')}
- Themes: {', '.join(metadata.get('themes', []))}
- Perfect for readers who enjoy: {metadata.get('genre', 'literary fiction')}

Why read this book:
This book offers a compelling story that explores {', '.join(metadata.get('themes', ['human nature'])[:3])}. 
{summary.split('.')[0]}. Readers will find themselves engaged with the narrative and its deeper meanings.
"""

        # Scrie fișierul
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Created: {filename}")

    print(f"\nSuccessfully created {len(book_summaries_dict)} book files!")


def create_books_index():
    """
    Creează un fișier index cu toate cărțile
    """
    content = "# Book Database Index\n\n"
    content += f"Total books: {len(book_summaries_dict)}\n\n"

    # Grupează pe genuri
    genres = {}
    for title, _ in book_summaries_dict.items():
        metadata = book_metadata.get(title, {})
        genre = metadata.get('genre', 'Unknown')
        if genre not in genres:
            genres[genre] = []
        genres[genre].append(title)

    for genre, books in sorted(genres.items()):
        content += f"## {genre}\n"
        for book in sorted(books):
            content += f"- {book}\n"
        content += "\n"

    with open("book_files/index.txt", 'w', encoding='utf-8') as f:
        f.write(content)

    print("Created: book_files/index.txt")


if __name__ == "__main__":
    create_individual_book_files()
    create_books_index()

    print("\n" + "=" * 50)
    print("IMPORTANT: Add these files to your project folder!")
    print("- book_files/ directory with all individual book files")
    print("- Each file follows the ## Title: format requested")
    print("=" * 50)