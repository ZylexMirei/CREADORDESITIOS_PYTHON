import sqlite3

def hacer_admin():
    print("\n--- CONVIRTIENDO USUARIO EN ADMIN ---")
    email = input("Introduce el CORREO del usuario: ")
    
    try:
        conn = sqlite3.connect('sitios.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ ¡ÉXITO! El usuario {email} ahora es ADMIN.")
        else:
            print(f"❌ Error: No se encontró el usuario {email}.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    hacer_admin()