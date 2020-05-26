import Models
import datetime
import dto.BookDTO
from Utils import BookUtils
from Constants.BookConstants import FIELDS_FOR_BOOK_UPDATE_REQUEST


class BookDAO:
    @staticmethod
    def create_new_book(book_dto, creator):
        book = Models.Book()
        try:
            new_book = BookUtils.convert_new_book_request_object_for_persistence(book_dto, book)
            if isinstance(new_book, str):
                return {'error': new_book}, 404
            new_book.created_by = Models.User.objects(email=creator.get('email'))
            new_book.last_updated_by = Models.User.objects(email=creator.get('email'))
            new_book.save()
            return {'response': dto.BookDTO.book_dto(new_book)}, 201
        except Exception as e:
            return {'error': f"Exception, {e}, occurred."}, 500

    @staticmethod
    def delete_book_by_id(book_id):
        book = Models.Book.objects(pk=str(book_id)).first()
        book.is_active = False
        book.last_updated_at = datetime.datetime.now()
        book.save()
        return {'response': 'Book was successfully removed.'}

    @staticmethod
    def update_book_by_id(req_book, updated_by):
        book = BookDAO.find_active_inactive_book_by_id(req_book.get('id'))
        if not book.is_active:
            return {'error': 'Cannot update an inactive book. Please restore the book to active first.'}, 403
        up_book = dto.BookDTO.book_dto(book)
        for field in FIELDS_FOR_BOOK_UPDATE_REQUEST:
            if field != "id" and req_book[field] and len(req_book[field].strip()) > 0:
                up_book[field] = req_book[field]
        validated_existence = BookDAO.find_by_name_author_genre(up_book)
        is_book_by_barcode = BookDAO.get_by_barcode(up_book.get('barcode'))
        if validated_existence and dto.BookDTO.book_dto(validated_existence).get('id') != req_book.get('id'):
            return {'error': 'Book with the same name already exists for this author.'}, 409
        if up_book.get(
                'barcode') and len(up_book.get(
                'barcode').strip()) > 1 and is_book_by_barcode and dto.BookDTO.book_dto(
                is_book_by_barcode).get('id') != req_book.get('id'):
            return {'error': 'Another book with the same barcode already exists. Please use a fresh barcode.'}, 409
        book.update(
            set__name=up_book.get('name') if up_book.get('name') else book.name,
            set__summary=up_book.get('summary') if up_book.get('summary') else book.summary,
            set__genre=up_book.get('genre') if up_book.get('genre') else book.summary,
            set__barcode=up_book.get('barcode') if up_book.get('barcode') else book.summary,
            set__author=up_book.get('author') if up_book.get('author') else book.summary,
            set__last_updated_by=Models.User.objects(email=updated_by.get('email')).first(),
            set__last_updated_at=datetime.datetime.now()
        )
        response = {
                       'response': {
                           'Success': 'Book Sucessfully updated.',
                           'updated_book': dto.BookDTO.book_dto(book)
                       }
                   }, 200
        return response

    @staticmethod
    def restore_inactive_book(book_id):
        book = Models.Book.objects(pk=str(book_id)).first()
        book.is_active = True
        book.last_updated_at = datetime.datetime.now()
        book.save()
        return {'response': 'Book was successfully restored.'}

    @staticmethod
    def find_by_created_by_user(email):
        all_books = []
        books = Models.Book.objects(created_by=email)
        for book in books:
            all_books.append(dto.BookDTO.book_dto(book))
        return all_books

    @staticmethod
    def find_all_active_books():
        books = Models.Book.objects(is_active=True)
        return books

    @staticmethod
    def find_book_by_author(author):
        books = Models.Book.objects(author=author)
        return books

    @staticmethod
    def find_by_name_author_genre(book):
        result_book = Models.Book.objects(name=book['name'], author=book['author'], genre=book['genre']).first()
        return result_book

    @staticmethod
    def find_active_inactive_book_by_id(book_id):
        book = Models.Book.objects(pk=str(book_id)).first()
        return book

    @staticmethod
    def find_active_book_by_id(book_id):
        book = Models.Book.objects(pk=str(book_id)).first()
        return book

    @staticmethod
    def get_by_barcode(barcode):
        book = Models.Book.objects(barcode=barcode).first()
        return book
