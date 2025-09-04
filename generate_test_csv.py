#!/usr/bin/env python
import csv
import random
import string
from datetime import datetime, timedelta

# Generate a CSV file with dummy data that's over 1MB
def generate_dummy_csv(filename="test_data.csv", target_size_mb=1.2):
    headers = [
        "ID", "Name", "Email", "Phone", "Address", "City", "State", "ZIP",
        "Country", "Company", "Department", "Job Title", "Salary", "Hire Date",
        "Status", "Notes", "Manager", "Project", "Budget", "Completion"
    ]
    
    cities = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Porto Alegre", "Salvador", "Brasília", "Curitiba", "Fortaleza", "Recife", "Manaus"]
    states = ["SP", "RJ", "MG", "RS", "BA", "DF", "PR", "CE", "PE", "AM"]
    departments = ["Sales", "Marketing", "Engineering", "HR", "Finance", "Operations", "IT", "Legal", "Customer Service", "R&D"]
    statuses = ["Active", "Inactive", "Pending", "Suspended", "Terminated"]
    
    target_size_bytes = target_size_mb * 1024 * 1024
    current_size = 0
    row_count = 0
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        
        while current_size < target_size_bytes:
            row = [
                row_count + 1,  # ID
                f"{random.choice(['João', 'Maria', 'Pedro', 'Ana', 'Carlos', 'Juliana', 'Paulo', 'Fernanda'])} {random.choice(['Silva', 'Santos', 'Oliveira', 'Souza', 'Lima', 'Pereira', 'Costa', 'Ferreira'])}",
                f"user{row_count}@company{random.randint(1, 100)}.com.br",
                f"+55 11 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                f"Rua {random.choice(['das Flores', 'Principal', 'São Paulo', 'Brasil', 'da Paz'])}, {random.randint(1, 999)}",
                random.choice(cities),
                random.choice(states),
                f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
                "Brazil",
                f"Company {random.randint(1, 500)}",
                random.choice(departments),
                f"{random.choice(['Senior', 'Junior', 'Mid-level'])} {random.choice(['Analyst', 'Manager', 'Developer', 'Specialist', 'Coordinator'])}",
                random.randint(3000, 25000),
                (datetime.now() - timedelta(days=random.randint(1, 3650))).strftime("%Y-%m-%d"),
                random.choice(statuses),
                ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=random.randint(20, 100))),
                f"Manager{random.randint(1, 50)}",
                f"Project-{random.randint(100, 999)}",
                random.randint(10000, 1000000),
                random.randint(0, 100)
            ]
            
            writer.writerow(row)
            row_count += 1
            
            # Estimate current file size (rough approximation)
            row_str = ','.join(str(item) for item in row)
            current_size += len(row_str.encode('utf-8')) + 2  # +2 for newline
    
    print(f"Generated {filename} with {row_count} rows")
    print(f"Approximate size: {current_size / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    generate_dummy_csv()