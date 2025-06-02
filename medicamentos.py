from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector
from datetime import datetime
from db import app, db_config


@app.route('/medicamentos', methods=['POST'])
@jwt_required()
@cross_origin()
def create_medicamento():
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['nombre', 'dosis', 'id_tratamiento']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        query = """
        INSERT INTO Medicamento (Nombre, Dosis, ID_Tratamiento)
        VALUES (%s, %s, %s)
        """
        
        values = (data['nombre'], data['dosis'], data['id_tratamiento'])
        cursor.execute(query, values)
        connection.commit()
        
        return jsonify({'message': 'Medicamento creado exitosamente', 'id': cursor.lastrowid}), 201
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/medicamentos/tratamiento/<int:tratamiento_id>', methods=['GET'])
@jwt_required()
@cross_origin()
def get_medicamentos_tratamiento(tratamiento_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT m.*, t.Descripción as descripcion_tratamiento
        FROM Medicamento m
        JOIN Tratamiento t ON m.ID_Tratamiento = t.ID_Tratamiento
        WHERE m.ID_Tratamiento = %s
        """
        cursor.execute(query, (tratamiento_id,))
        medicamentos = cursor.fetchall()
        
        return jsonify({'medicamentos': medicamentos})
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()