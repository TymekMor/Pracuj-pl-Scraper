import os
from azure.data.tables import TableClient, UpdateMode
from azure.core.exceptions import ResourceNotFoundError
from datetime import datetime
import hashlib

class AzureTableManager:
    def __init__(self, connection_string):
        self.connection_string = connection_string

    def _get_client(self, table_name):
        # Automatyczne tworzenie tabeli, jeśli nie istnieje
        client = TableClient.from_connection_string(self.connection_string, table_name=table_name)
        try:
            client.create_table()
        except:
            pass
        return client

    def save_offers(self, offers, group_name):
        """
        Zapisuje oferty do tabeli przypisanej do grupy (np. 'OffersHR' lub 'OffersSales').
        """
        if not offers:
            return
            
        table_name = f"Offers{group_name}"
        client = self._get_client(table_name)
        
        for offer in offers:
            # PartitionKey: Słowo kluczowe
            # RowKey: Hash z linku (musi być unikalny i nie może mieć znaków specjalnych)
            row_key = hashlib.md5(offer['Link'].encode()).hexdigest()
            
            entity = {
                "PartitionKey": offer['Keyword'],
                "RowKey": row_key,
                "Title": offer['Title'],
                "Company": offer['Company'],
                "Salary": offer['Salary'],
                "Location": offer['Location'],
                "Link": offer['Link'],
                "Requirements": offer['Requirements'],
                "ScrapedAt": datetime.utcnow().isoformat()
            }
            
            # Upsert (Update or Insert)
            client.upsert_entity(mode=UpdateMode.MERGE, entity=entity)