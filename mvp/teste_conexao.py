import os
from dotenv import load_dotenv
from databricks import sql

load_dotenv()

print("Conectando ao Databricks...")

try:
    with sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    ) as conexao:

        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM workspace.alertavida.gold_mvp_alertas
                ORDER BY data_evento DESC
            """)

            resultados = cursor.fetchall()

            print("\nConexão realizada com sucesso!")
            print(f"Total de alertas encontrados: {len(resultados)}")
            print("\nAlertas:")

            for alerta in resultados:
                print(alerta)

except Exception as erro:
    print("\nErro ao conectar ou consultar o Databricks:")
    print(erro)