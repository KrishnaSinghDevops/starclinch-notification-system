from django.db import connection , transaction


# for select query
def db_connect(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columes = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columes, row))
                for row in rows]

# for insert and update

def exel_query(query, params = None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        return cursor.rowcount
    

# user = testuser
# pass = Test@12345

