from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector
from datetime import datetime
from db import app, db_config


@app.route('/tratamientos', methods=['POST'])
@jwt_required()
@cross_origin()
def create_tratamiento():
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['descripcion', 'fecha_inicio', 'id_diagnostico']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        query = """
        INSERT INTO Tratamiento (Descripción, Fecha_Inicio, Fecha_Fin, ID_Diagnóstico)
        VALUES (%s, %s, %s, %s)
        """
        
        values = (data['descripcion'], data['fecha_inicio'], data.get('fecha_fin'), data['id_diagnostico'])
        cursor.execute(query, values)
        connection.commit()
        
        return jsonify({'message': 'Tratamiento creado exitosamente', 'id': cursor.lastrowid}), 201
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
