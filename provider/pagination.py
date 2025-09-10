from rest_framework.pagination import PageNumberPagination

class DocumentPagination(PageNumberPagination):
    page_size = 1
    page_size_query_param = 'limit'  
    max_page_size = 100  
