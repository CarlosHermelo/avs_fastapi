#!/usr/bin/env python
# BD_RELA/test_usuario_321.py
from sqlalchemy.orm import sessionmaker
from create_tables import Usuario, get_engine

def crear_usuario_321():
    """Crea el usuario con ID 321 para que el sistema pueda usarlo por defecto"""
    
    # Obtener motor y crear sesión
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Verificar si ya existe el usuario
        print("Verificando si existe el usuario 321...")
        
        # Intenta obtener el usuario por ID
        try:
            usuario_existente = session.get(Usuario, 321)
            if usuario_existente:
                print(f"El usuario con ID 321 ya existe: {usuario_existente.nombre} ({usuario_existente.ugel_origen})")
                return True
        except Exception as e:
            print(f"Error al verificar usuario existente: {str(e)}")
            pass  # Continuar con la creación
        
        print("Creando usuario con ID 321...")
        # Crear el usuario con ID específico
        usuario = Usuario(
            id_usuario=321,
            nombre="Usuario SIMAP Predeterminado",
            ugel_origen="Formosa"
        )
        
        # Guardar en la base de datos
        session.add(usuario)
        session.commit()
        
        print(f"Se ha creado el usuario con ID 321: {usuario.nombre} ({usuario.ugel_origen})")
        
        # Cerrar sesión
        session.close()
        return True
        
    except Exception as e:
        print(f"Error al crear usuario 321: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False

if __name__ == "__main__":
    print("Creando usuario predeterminado para el sistema...")
    crear_usuario_321()
    print("\nEjecute 'python listar_usuarios.py' para verificar") 