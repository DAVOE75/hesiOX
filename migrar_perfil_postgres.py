"""
Migración: Agregar campo perfil_analisis a la tabla proyectos (PostgreSQL)
"""

from app import app, db
from sqlalchemy import text
import traceback

print("🔄 Iniciando migración de perfil_analisis...")

with app.app_context():
    try:
        # Verificar si la columna ya existe
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'proyectos' 
            AND column_name = 'perfil_analisis'
        """)
        
        result = db.session.execute(check_query)
        exists = result.fetchone()
        
        if exists:
            print("⚠️  La columna perfil_analisis ya existe")
        else:
            print("📝 Agregando columna perfil_analisis...")
            
            # Agregar columna perfil_analisis
            db.session.execute(text("""
                ALTER TABLE proyectos 
                ADD COLUMN perfil_analisis TEXT DEFAULT 'contenido'
            """))
            
            db.session.commit()
            print("✅ Columna perfil_analisis agregada")
        
        # Actualizar proyectos existentes según su tipo
        print("📝 Actualizando proyectos existentes...")
        
        # Hemerografía y archivos -> contenido
        result1 = db.session.execute(text("""
            UPDATE proyectos 
            SET perfil_analisis = 'contenido' 
            WHERE tipo IN ('hemerografia', 'archivos', 'mixto')
            AND (perfil_analisis IS NULL OR perfil_analisis = '')
        """))
        
        # Libros -> estilometrico
        result2 = db.session.execute(text("""
            UPDATE proyectos 
            SET perfil_analisis = 'estilometrico' 
            WHERE tipo = 'libros'
            AND (perfil_analisis IS NULL OR perfil_analisis = '')
        """))
        
        db.session.commit()
        
        print(f"✅ {result1.rowcount + result2.rowcount} proyectos actualizados")
        
        # Verificar
        print("\n📊 Verificando proyectos:")
        result = db.session.execute(text("""
            SELECT id, nombre, tipo, perfil_analisis 
            FROM proyectos 
            ORDER BY id
            LIMIT 10
        """))
        
        for row in result:
            print(f"  {row.id:3d} | {row.nombre[:30]:30s} | {row.tipo:15s} | {row.perfil_analisis}")
        
        print("\n✅ Migración completada exitosamente")
            
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error durante la migración:")
        print(f"   {str(e)}")
        print("\n📋 Traceback completo:")
        traceback.print_exc()
