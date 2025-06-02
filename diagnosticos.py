from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector
from datetime import datetime
from db import app, db_config

@app.route('/diagnosticos/crear', methods=['POST'])
@cross_origin()
def create_diagnostico_with_patient():
    cursor = None
    connection = None
    try:
        app.logger.info("Received request to create diagnosis")
        data = request.get_json()
        
        if not data:
            app.logger.error("No data provided in request")
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
            
        # Validate required fields
        required_fields = ['descripcion', 'id_paciente', 'id_cita']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            app.logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Convert to proper types
        try:
            id_paciente = int(data['id_paciente'])
            id_cita = int(data['id_cita'])
        except (ValueError, TypeError) as e:
            app.logger.error(f"Invalid ID format: {e}")
            return jsonify({
                'success': False,
                'error': 'Invalid ID format - must be integers'
            }), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Get patient's medical history
        history_query = """
        SELECT ID_Historial 
        FROM Historial_Médico 
        WHERE ID_Paciente = %s
        ORDER BY Fecha_Creación DESC
        LIMIT 1
        """
        cursor.execute(history_query, (id_paciente,))
        history = cursor.fetchone()
        
        if not history:
            app.logger.warning(f"No medical history found for patient {id_paciente}")
            return jsonify({
                'success': False,
                'error': f'No medical history found for patient ID {id_paciente}'
            }), 404
        
        id_historial = history['ID_Historial']
        
        # Verify appointment exists and belongs to the patient
        appointment_query = """
        SELECT ID_Cita, Fecha, Hora, Estado 
        FROM Cita 
        WHERE ID_Cita = %s AND ID_Paciente = %s
        """
        cursor.execute(appointment_query, (id_cita, id_paciente))
        appointment = cursor.fetchone()
        
        if not appointment:
            app.logger.warning(f"Appointment {id_cita} not found for patient {id_paciente}")
            return jsonify({
                'success': False,
                'error': f'Appointment not found or does not belong to patient'
            }), 404
        
        # Create the diagnosis
        fecha_diagnostico = data.get('fecha', datetime.now().date())
        
        diagnosis_query = """
        INSERT INTO Diagnóstico (Descripción, Fecha, ID_Historial, ID_Cita)
        VALUES (%s, %s, %s, %s)
        """
        
        values = (
            data['descripcion'],
            fecha_diagnostico,
            id_historial,
            id_cita
        )
        
        cursor.execute(diagnosis_query, values)
        diagnosis_id = cursor.lastrowid
        connection.commit()
        
        # Get complete diagnosis information for response
        try:
            complete_query = """
            SELECT 
                d.ID_Diagnóstico,
                d.Descripción,
                DATE_FORMAT(d.Fecha, '%Y-%m-%d') as Fecha,
                d.ID_Historial,
                d.ID_Cita
            FROM Diagnóstico d
            WHERE d.ID_Diagnóstico = %s
            """
            
            cursor.execute(complete_query, (diagnosis_id,))
            complete_diagnosis = cursor.fetchone()
            
            # If the basic query works, try to get additional info
            if complete_diagnosis:
                try:
                    extended_query = """
                    SELECT 
                        d.ID_Diagnóstico,
                        d.Descripción,
                        DATE_FORMAT(d.Fecha, '%Y-%m-%d') as Fecha,
                        d.ID_Historial,
                        d.ID_Cita,
                        p.ID_Paciente,
                        p.Nombre as nombre_paciente,
                        DATE_FORMAT(c.Fecha, '%Y-%m-%d') as fecha_cita,
                        TIME_FORMAT(c.Hora, '%H:%i:%s') as hora_cita,
                        m.Nombre as nombre_medico
                    FROM Diagnóstico d
                    JOIN Historial_Médico h ON d.ID_Historial = h.ID_Historial
                    JOIN Paciente p ON h.ID_Paciente = p.ID_Paciente
                    JOIN Cita c ON d.ID_Cita = c.ID_Cita
                    JOIN Médico m ON c.ID_Médico = m.ID_Médico
                    WHERE d.ID_Diagnóstico = %s
                    """
                    
                    cursor.execute(extended_query, (diagnosis_id,))
                    extended_result = cursor.fetchone()
                    
                    if extended_result:
                        complete_diagnosis = extended_result
                    
                except mysql.connector.Error as join_error:
                    app.logger.warning(f"Could not fetch extended diagnosis info: {join_error}")
                    # Continue with basic diagnosis info
                    
        except mysql.connector.Error as query_error:
            app.logger.error(f"Error fetching diagnosis info: {query_error}")
            # Return basic success response without detailed diagnosis info
            complete_diagnosis = {
                'ID_Diagnóstico': diagnosis_id,
                'Descripción': data['descripcion'],
                'Fecha': str(fecha_diagnostico),
                'ID_Historial': id_historial,
                'ID_Cita': id_cita
            }
        
        app.logger.info(f"Diagnosis created successfully for patient {id_paciente}")
        
        return jsonify({
            'success': True,
            'message': 'Diagnosis created successfully',
            'diagnostico': complete_diagnosis
        }), 201
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error: {str(error)}")
        if connection:
            connection.rollback()
        return jsonify({
            'success': False,
            'error': 'Database operation failed'
        }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        if connection:
            connection.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
@app.route('/diagnosticos', methods=['GET'])
@jwt_required()
@cross_origin()
def get_diagnosticos():
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        

        id_historial = request.args.get('id_historial')
        id_cita = request.args.get('id_cita')
        fecha = request.args.get('fecha')
        
        query = """
        SELECT 
            d.ID_Diagnóstico,
            d.Descripción,
            DATE_FORMAT(d.Fecha, '%Y-%m-%d') as Fecha,
            d.ID_Historial,
            d.ID_Cita,
            h.ID_Paciente,
            p.Nombre as nombre_paciente
        FROM Diagnóstico d
        JOIN Historial_Médico h ON d.ID_Historial = h.ID_Historial
        JOIN Paciente p ON h.ID_Paciente = p.ID_Paciente
        WHERE 1=1
        """
        
        params = []
        
        if id_historial:
            query += " AND d.ID_Historial = %s"
            params.append(id_historial)
            
        if id_cita:
            query += " AND d.ID_Cita = %s"
            params.append(id_cita)
            
        if fecha:
            query += " AND DATE(d.Fecha) = %s"
            params.append(fecha)
        
        query += " ORDER BY d.Fecha DESC"
        
        cursor.execute(query, params)
        diagnosticos = cursor.fetchall()
        
        return jsonify({
            'count': len(diagnosticos),
            'diagnosticos': diagnosticos
        })
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error: {str(error)}")
        return jsonify({'error': 'Error de base de datos'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Error inesperado'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()