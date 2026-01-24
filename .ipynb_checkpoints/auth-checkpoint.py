import os
from azure.data.tables import TableClient
from werkzeug.security import check_password_hash, generate_password_hash

class AuthManager:
    def __init__(self, connection_string):
        self.client = TableClient.from_connection_string(connection_string, table_name="Users")

    def verify_user(self, email, password):
        try:
            # Szukamy użytkownika po adresie email (RowKey)
            user = self.client.get_entity(partition_key="Segula", row_key=email)
            
            # Sprawdzamy czy hash hasła się zgadza
            if check_password_hash(user['Password'], password):
                return {
                    "email": user['RowKey'],
                    "name": user['FullName'],
                    "group": user['Group']
                }
        except Exception as e:
            print(f"Błąd autoryzacji: {e}")
        return None

# Pomocnicza do generowania hashy (użyj jej, by stworzyć hasło do bazy)
def create_password_hash(password):
    return generate_password_hash(password)