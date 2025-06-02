from db import app
if __name__ == '__main__':
    # app.run(host='172.31.86.111', port=8080)
    try:
        app.run(host='172.31.86.111', port=8080)
    except (KeyboardInterrupt, SystemExit):
        print("Exiting...")
 