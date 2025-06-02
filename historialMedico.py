from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector
from datetime import datetime
from db import app, db_config

@app.route('/historial', methods=['POST'])
@jwt_required()
@cross_origin()
def create_historial():
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['id_paciente']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Verificar que el paciente exista
        cursor.execute("SELECT COUNT(*) FROM Paciente WHERE ID_Paciente = %s", (data['id_paciente'],))
        if cursor.fetchone()[0] == 0:
            return jsonify({'error': 'Paciente no encontrado'}), 404
        
        fecha_creacion = data.get('fecha_creacion', datetime.now().date())
        
        query = """
        INSERT INTO Historial_Médico (ID_Paciente, Fecha_Creación)
        VALUES (%s, %s)
        """
        
        values = (data['id_paciente'], fecha_creacion)
        cursor.execute(query, values)
        connection.commit()
        
        return jsonify({'message': 'Historial médico creado exitosamente', 'id': cursor.lastrowid}), 201
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/historial/paciente/<int:paciente_id>', methods=['GET'])
@cross_origin()
def get_historial_paciente(paciente_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
   
        historial_query = """
        SELECT 
            h.ID_Historial,
            h.ID_Paciente,
            DATE_FORMAT(h.Fecha_Creación, '%Y-%m-%d') as Fecha_Creación,
            p.Nombre as nombre_paciente
        FROM Historial_Médico h
        JOIN Paciente p ON h.ID_Paciente = p.ID_Paciente
        WHERE h.ID_Paciente = %s
        ORDER BY h.Fecha_Creación DESC
        """
        cursor.execute(historial_query, (paciente_id,))
        historiales = cursor.fetchall()
        
        if not historiales:
            return jsonify({'message': 'No se encontraron registros de historial para este paciente'}), 404
        
       
        for historial in historiales:
            diagnostico_query = """
            SELECT 
                d.ID_Diagnóstico,
                d.Descripción,
                DATE_FORMAT(d.Fecha, '%Y-%m-%d') as Fecha,
                d.ID_Historial,
                d.ID_Cita
            FROM Diagnóstico d
            WHERE d.ID_Historial = %s
            ORDER BY d.Fecha DESC
            """
            cursor.execute(diagnostico_query, (historial['ID_Historial'],))
            diagnosticos = cursor.fetchall()
            
           
            historial['diagnosticos'] = diagnosticos if diagnosticos else []
        
        return jsonify(historiales)
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error in get_historial_paciente: {error}")
        return jsonify({'error': 'Error de base de datos'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in get_historial_paciente: {e}")
        return jsonify({'error': 'Error inesperado'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()