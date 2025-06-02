from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector
from datetime import datetime
from db import app, db_config

@app.route('/roles', methods=['GET'])
@jwt_required()
@cross_origin()
def get_roles():
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM Rol ORDER BY Nombre"
        cursor.execute(query)
        roles = cursor.fetchall()
        
        return jsonify({'roles': roles})
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/roles', methods=['POST'])

@cross_origin()
def create_rol():
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data or 'nombre' not in data:
            return jsonify({'error': 'Nombre del rol es requerido'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        query = "INSERT INTO Rol (Nombre) VALUES (%s)"
        cursor.execute(query, (data['nombre'],))
        connection.commit()
        
        return jsonify({'message': 'Rol creado exitosamente', 'id': cursor.lastrowid}), 201
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()