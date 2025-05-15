#!/usr/bin/env python
# BD_RELA/listar_usuarios.py
from sqlalchemy import select, inspect, text
from sqlalchemy.orm import sessionmaker
from create_tables import Usuario, get_engine

def listar_usuarios(show_all=False):
    # Obtener engine y crear sesión
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Verificar si la tabla existe
        inspector = inspect(engine)
        if "usuarios" not in inspector.get_table_names():
            print("La tabla 'usuarios' no existe en la base de datos.")
            return
        
        # Consultar usuarios
        if show_all:
            # Consulta SQL directa para ver todos los usuarios
            result = session.execute(text("SELECT id_usuario, nombre, ugel_origen FROM usuarios ORDER BY id_usuario"))
            usuarios = result.fetchall()
        else:
            # Consulta usando ORM
            usuarios = session.execute(select(Usuario)).scalars().all()
        
        print("\nUsuarios existentes en la base de datos:")
        print("=" * 50)
        
        if not usuarios:
            print("No hay usuarios registrados.")
        else:
            # Cuando hay resultados
            user_count = 0
            for u in usuarios:
                user_count += 1
                if show_all:
                    print(f"ID: {u[0]}, Nombre: {u[1]}, UGL: {u[2]}")
                else:
                    print(f"ID: {u.id_usuario}, Nombre: {u.nombre}, UGL: {u.ugel_origen}")
            
            # Verificar el usuario 321 explícitamente
            if show_all:
                try:
                    # Ver si hay usuario con ID 321
                    usuario_321 = session.execute(text("SELECT id_usuario, nombre, ugel_origen FROM usuarios WHERE id_usuario = 321")).fetchone()
                    if usuario_321:
                        print(f"\nUsuario predeterminado:")
                        print(f"ID: {usuario_321[0]}, Nombre: {usuario_321[1]}, UGL: {usuario_321[2]}")
                except Exception as e:
                    print(f"Error buscando usuario 321: {str(e)}")
        
        print("=" * 50)
        
        # Cerrar sesión
        session.close()
    
    except Exception as e:
        print(f"Error al consultar usuarios: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    show_all = "--all" in sys.argv
    if "--help" in sys.argv:
        print("Uso: python listar_usuarios.py [--all]")
        print("  --all: Muestra todos los usuarios, incluso aquellos con IDs específicos")
        sys.exit(0)
    
    listar_usuarios(show_all) 