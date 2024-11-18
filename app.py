from flask import Flask, jsonify, request, send_from_directory
import tabula
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from flask_cors import CORS
import os
import glob

app = Flask(__name__)
CORS(app)

DATABASE_URL = "sqlite:///notas_fiscais.db"
engine = create_engine(DATABASE_URL)

UPLOAD_FOLDER = 'uploads'  # Pasta onde os arquivos serão armazenados
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CONVERTED_FOLDER = 'converted'  # Pasta para armazenar os arquivos convertidos
if not os.path.exists(CONVERTED_FOLDER):
    os.makedirs(CONVERTED_FOLDER)

# Função para criar a tabela no banco de dados
def criar_tabela():
    try:
        df = pd.DataFrame(columns=["id", "empresa", "valor", "data"])
        df.to_sql("notas_fiscais", con=engine, if_exists="replace", index=False)
    except SQLAlchemyError as e:
        print("Erro ao criar a tabela:", e)

# Endpoint para o upload do PDF
@app.route("/upload", methods=["POST"])
def upload_nota():
    file = request.files['file']
    if not file:
        return jsonify({"message": "Nenhum arquivo enviado"}), 400
    
    # Salvar o arquivo PDF na pasta 'uploads'
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    return jsonify({"message": "Arquivo PDF carregado com sucesso!", "file_path": file_path}), 200

# Endpoint para conversão do PDF para Excel

@app.route("/convert", methods=["POST"])
def converter_pdf_para_excel():
    # Identificar o arquivo PDF mais recente na pasta 'uploads'
    try:
        files = glob.glob(os.path.join(UPLOAD_FOLDER, "*.pdf"))  # Todos os PDFs na pasta
        if not files:
            return jsonify({"message": "Nenhum arquivo PDF encontrado na pasta 'uploads'"}), 404

        # Encontrar o arquivo mais recente
        latest_file = max(files, key=os.path.getctime)

        # Abrir o arquivo PDF
        tables = tabula.read_pdf(latest_file, pages='all', multiple_tables=True)

        if not tables:
            return jsonify({"message": "Nenhuma tabela encontrada no PDF"}), 404


        # Gerar o arquivo Excel na pasta 'converted'
        output_xlsx_path = os.path.join(CONVERTED_FOLDER, os.path.basename(latest_file).replace('.pdf', '.xlsx'))
        with pd.ExcelWriter(output_xlsx_path, engine='openpyxl') as writer:
            for i, table in enumerate(tables):
                sheet_name = f"Tabela_{i+1}"  # Nome da aba
                table.to_excel(writer, index=False, sheet_name=sheet_name)
    

        return jsonify({"message": "Arquivo Excel gerado com sucesso!", "file_path": output_xlsx_path}), 200

    except Exception as e:
        return jsonify({"message": f"Erro ao processar o PDF: {e}"}), 500
    
# Endpoint para download do arquivo Excel
@app.route("/download/<filename>", methods=["GET"])
def download_excel(filename):
    # Enviar o arquivo Excel para o usuário
    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)

# Endpoint para obter as notas fiscais do banco
@app.route("/notas", methods=["GET"])
def obter_notas():
    try:
        df = pd.read_sql("SELECT * FROM notas_fiscais", con=engine)
        return jsonify(df.to_dict(orient="records")), 200
    except SQLAlchemyError as e:
        return jsonify({"message": f"Erro ao obter as notas fiscais: {e}"}), 500
    except Exception as e:
        return jsonify({"message": f"Erro inesperado: {e}"}), 500

if __name__ == "__main__":
    criar_tabela()
    app.run(debug=True)
