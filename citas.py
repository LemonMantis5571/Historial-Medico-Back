from db import app, db_config
from flask_cors import cross_origin
from flask import jsonify, request
import mysql.connector
from flask_jwt_extended import jwt_required

from datetime import datetime

@app.route('/citas', methods=['POST'])
@cross_origin()
def create_cita():
    cursor = None
    connection = None
    try:
        app.logger.info("Citas endpoint called")
        
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        app.logger.info(f"Received data: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided', 'received': False}), 400
            
        required_fields = ['fecha', 'hora', 'id_paciente', 'id_medico']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing fields: {missing_fields}',
                'received_data': data
            }), 400
        
        # Type validation
        try:
            id_paciente = int(data['id_paciente'])
            id_medico = int(data['id_medico'])
        except (ValueError, TypeError):
            return jsonify({'error': 'IDs must be integers'}), 400
        
        # Date validation
        try:
            datetime.strptime(data['fecha'], '%Y-%m-%d')
            datetime.strptime(data['hora'], '%H:%M:%S')
        except ValueError as e:
            return jsonify({'error': f'Invalid date/time format: {str(e)}'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Check patient exists
        cursor.execute("SELECT 1 FROM Paciente WHERE ID_Paciente = %s", (id_paciente,))
        if not cursor.fetchone():
            return jsonify({'error': 'Patient not found'}), 404
            
        # Check doctor exists
        cursor.execute("SELECT 1 FROM Médico WHERE ID_Médico = %s", (id_medico,))
        if not cursor.fetchone():
            return jsonify({'error': 'Doctor not found'}), 404
        
        estado = data.get('estado', 'Pendiente')
        
        query = """
        INSERT INTO Cita (Fecha, Hora, ID_Paciente, ID_Médico, Estado)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (data['fecha'], data['hora'], id_paciente, id_medico, estado))
        connection.commit()
        
        return jsonify({
            'success': True,
            'id': cursor.lastrowid,
            'fecha': data['fecha'],
            'hora': data['hora'],
            'id_paciente': id_paciente,
            'id_medico': id_medico,
            'estado': estado
        }), 201
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error: {str(error)}")
        return jsonify({'error': 'Database operation failed'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/citas/medico/<int:medico_id>', methods=['GET'])
@cross_origin()
def get_citas_by_medico(medico_id):
    app.logger.info(f"Received request for doctor ID: {medico_id}")
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        app.logger.info("Checking if doctor exists...")
        cursor.execute("SELECT ID_Médico, Nombre FROM Médico WHERE ID_Médico = %s", (medico_id,))
        doctor = cursor.fetchone()
        
        if not doctor:
            app.logger.warning(f"Doctor {medico_id} not found")
            return jsonify({'error': 'Doctor not found'}), 404
        
        app.logger.info(f"Doctor found: {doctor['Nombre']}")
        
        query = """
        SELECT 
            c.ID_Cita,
            c.Fecha,
            c.Hora,
            c.Estado,
            p.ID_Paciente,
            p.Teléfono,
            p.Nombre as nombre_paciente,
            m.ID_Médico,
            m.Nombre as nombre_medico, 
            m.Especialidad
        FROM Cita c
        JOIN Paciente p ON c.ID_Paciente = p.ID_Paciente
        JOIN Médico m ON c.ID_Médico = m.ID_Médico
        WHERE c.ID_Médico = %s
        ORDER BY c.Fecha, c.Hora
        """
        app.logger.info("Fetching appointments...")
        cursor.execute(query, (medico_id,))
        citas = cursor.fetchall()
        
        app.logger.info(f"Found {len(citas)} appointments")
        
        # Convert dates and times to string
        for cita in citas:
            if cita['Fecha']:
                cita['Fecha'] = cita['Fecha'].strftime('%Y-%m-%d')
            if cita['Hora']:
                cita['Hora'] = str(cita['Hora'])
        
        return jsonify({
            'success': True,
            'citas': citas,
            'total': len(citas),
            'medico': doctor
        })
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error: {str(error)}")
        return jsonify({'error': 'Database operation failed'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            


@app.route('/citas/<int:cita_id>', methods=['DELETE'])
@cross_origin()
def delete_cita(cita_id):
    cursor = None
    connection = None
    try:
        app.logger.info(f"Received request to delete appointment ID: {cita_id}")
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # First verify the appointment exists
        cursor.execute("SELECT ID_Cita FROM Cita WHERE ID_Cita = %s", (cita_id,))
        if not cursor.fetchone():
            app.logger.warning(f"Appointment {cita_id} not found")
            return jsonify({
                'success': False,
                'error': f'Appointment with ID {cita_id} not found'
            }), 404
        
        # Delete the appointment
        delete_query = "DELETE FROM Cita WHERE ID_Cita = %s"
        cursor.execute(delete_query, (cita_id,))
        connection.commit()
        
        app.logger.info(f"Successfully deleted appointment {cita_id}")
        return jsonify({
            'success': True,
            'message': f'Appointment {cita_id} deleted successfully',
            'deleted_id': cita_id
        }), 200
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error deleting appointment: {str(error)}")
        if connection:
            connection.rollback()
        return jsonify({
            'success': False,
            'error': 'Database operation failed',
            'details': str(error)
        }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error deleting appointment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            
@app.route('/citas/<int:cita_id>', methods=['PUT'])
@cross_origin()
def update_cita(cita_id):
    cursor = None
    connection = None
    try:
        app.logger.info(f"Received request to update appointment ID: {cita_id}")
        data = request.get_json()
        
        if not data:
            app.logger.error("No data provided in request")
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
            
        # Validate required fields
        required_fields = ['fecha', 'hora', 'id_paciente', 'id_medico', 'estado']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            app.logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Verify appointment exists
        cursor.execute("SELECT ID_Cita FROM Cita WHERE ID_Cita = %s", (cita_id,))
        if not cursor.fetchone():
            app.logger.warning(f"Appointment {cita_id} not found")
            return jsonify({
                'success': False,
                'error': f'Appointment with ID {cita_id} not found'
            }), 404
        
        # Verify patient exists
        cursor.execute("SELECT 1 FROM Paciente WHERE ID_Paciente = %s", (data['id_paciente'],))
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'error': 'Patient not found'
            }), 404
            
        # Verify doctor exists
        cursor.execute("SELECT 1 FROM Médico WHERE ID_Médico = %s", (data['id_medico'],))
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'error': 'Doctor not found'
            }), 404
        
        # Update appointment
        update_query = """
        UPDATE Cita 
        SET Fecha = %s,
            Hora = %s,
            ID_Paciente = %s,
            ID_Médico = %s,
            Estado = %s
        WHERE ID_Cita = %s
        """
        values = (
            data['fecha'],
            data['hora'],
            data['id_paciente'],
            data['id_medico'],
            data['estado'],
            cita_id
        )
        
        cursor.execute(update_query, values)
        connection.commit()
        
  
        cursor.execute("""
        SELECT 
            c.ID_Cita,
            c.Fecha,
            c.Hora,
            c.Estado,
            p.Nombre as nombre_paciente,
            p.Teléfono as telefono_paciente,
            m.Nombre as nombre_medico,
            m.Especialidad
        FROM Cita c
        JOIN Paciente p ON c.ID_Paciente = p.ID_Paciente
        JOIN Médico m ON c.ID_Médico = m.ID_Médico
        WHERE c.ID_Cita = %s
        """, (cita_id,))
        
        updated_cita = cursor.fetchone()
        
        # Format dates
        if updated_cita['Fecha']:
            updated_cita['Fecha'] = updated_cita['Fecha'].strftime('%Y-%m-%d')
        if updated_cita['Hora']:
            updated_cita['Hora'] = str(updated_cita['Hora'])
        
        app.logger.info(f"Successfully updated appointment {cita_id}")
        return jsonify({
            'success': True,
            'message': 'Appointment updated successfully',
            'cita': updated_cita
        }), 200
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error updating appointment: {str(error)}")
        if connection:
            connection.rollback()
        return jsonify({
            'success': False,
            'error': 'Database operation failed',
            'details': str(error)
        }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error updating appointment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/citas/paciente/<int:paciente_id>', methods=['GET'])
@cross_origin()
def get_citas_by_paciente(paciente_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Verify patient exists
        cursor.execute("SELECT 1 FROM Paciente WHERE ID_Paciente = %s", (paciente_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Patient not found'}), 404
        
        # Get appointments with doctor's name
        query = """
        SELECT 
            c.ID_Cita,
            c.Fecha,
            c.Hora,
            c.ID_Paciente,
            c.ID_Médico,
            c.Estado,
            m.Nombre as nombre_medico
        FROM Cita c
        JOIN Médico m ON c.ID_Médico = m.ID_Médico
        WHERE c.ID_Paciente = %s
        ORDER BY c.Fecha DESC, c.Hora DESC
        """
        cursor.execute(query, (paciente_id,))
        citas = cursor.fetchall()
        
        # Format the response
        formatted_citas = []
        for cita in citas:
            formatted_citas.append({
                'ID_Cita': cita['ID_Cita'],
                'Fecha': str(cita['Fecha']),  # Convertir a string
                'Hora': str(cita['Hora']),    # Convertir a string
                'ID_Paciente': cita['ID_Paciente'],
                'ID_Médico': cita['ID_Médico'],
                'Estado': cita['Estado'],
                'Medico': cita['nombre_medico']
            })
        
        return jsonify({
            'success': True,
            'citas': formatted_citas
        })
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()