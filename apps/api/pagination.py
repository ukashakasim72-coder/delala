from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class PropertyPagination(PageNumberPagination):
    """
    Custom pagination tailored for React Native lists (Infinite Scroll / FlatList).
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'has_next': self.get_next_link() is not None,  # Clean boolean flag for mobile loops
            'results': data
        })