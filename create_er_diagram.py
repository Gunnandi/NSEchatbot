import mysql.connector
import os
import networkx as nx
import matplotlib.pyplot as plt

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "password"
MYSQL_DB = "bankexchange"
ER_PATH = os.path.join('data', 'er_diagram.jpeg')

def get_schema_and_fks():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    schema = {}
    fks = []
    for table_name in tables:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        columns = cursor.fetchall()
        schema[table_name] = [col[0] for col in columns]
        # Get foreign keys
        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
        create_stmt = cursor.fetchone()[1]
        for line in create_stmt.split('\n'):
            if 'FOREIGN KEY' in line:
                parts = line.strip().split()
                from_col = parts[2].strip('`()')
                to_table = parts[4].strip('`()')
                to_col = parts[5].strip('`()')
                fks.append((table_name, from_col, to_table, to_col))
    conn.close()
    return schema, fks

def plot_er_diagram(schema, fks, path):
    G = nx.DiGraph()
    for table, columns in schema.items():
        G.add_node(table, label=f"{table}\n" + "\n".join(columns))
    for from_table, from_col, to_table, to_col in fks:
        G.add_edge(from_table, to_table, label=f"{from_col}→{to_col}")
    pos = nx.spring_layout(G, k=1.5, seed=42)
    plt.figure(figsize=(14, 8))
    nx.draw_networkx_nodes(G, pos, node_color='skyblue', node_size=2500)
    nx.draw_networkx_edges(G, pos, arrowstyle='-|>', arrowsize=20, edge_color='gray')
    labels = {n: f"{n}\n" + "\n".join(schema[n][:3]) + ("..." if len(schema[n]) > 3 else "") for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=9)
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    plt.title('ER Diagram')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(path, format='jpeg')
    plt.close()
    print(f'ER diagram written to {path}')

def main():
    schema, fks = get_schema_and_fks()
    plot_er_diagram(schema, fks, ER_PATH)

if __name__ == '__main__':
    main() 