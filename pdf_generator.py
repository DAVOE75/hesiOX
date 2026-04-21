"""
============================================================
GENERADOR DE PDF PARA ARTÍCULOS CIENTÍFICOS
============================================================
Genera PDFs con formato académico siguiendo plantillas:
- JANUS (revista médica)
- JSTOR (estándar académico)
- APA (American Psychological Association)

Incluye:
- Portada con logo institucional
- Resumen/Abstract bilingüe
- Cuerpo del artículo con secciones
- Referencias bibliográficas formateadas
- Numeración de páginas
- Encabezados y pie de página
============================================================
"""

from io import BytesIO
from datetime import datetime
import re
import json
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image, KeepTogether
)
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    """Elimina tags HTML para texto plano"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data)
    
    def get_data(self):
        return ''.join(self.text)


def strip_html_tags(html):
    """Convierte HTML a texto plano"""
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


def html_to_reportlab(html_content):
    """
    Convierte HTML de Quill.js a formato ReportLab
    Soporta: <p>, <strong>, <em>, <u>, <ol>, <ul>, <li>, <blockquote>, <a>
    """
    if not html_content:
        return ""
    
    # Conversiones básicas
    html = html_content.replace('<strong>', '<b>').replace('</strong>', '</b>')
    html = html.replace('<em>', '<i>').replace('</em>', '</i>')
    html = html.replace('<h1>', '<b><font size="16">').replace('</h1>', '</font></b><br/>')
    html = html.replace('<h2>', '<b><font size="14">').replace('</h2>', '</font></b><br/>')
    html = html.replace('<h3>', '<b><font size="12">').replace('</h3>', '</font></b><br/>')
    html = html.replace('<br>', '<br/>')
    html = html.replace('</p><p>', '<br/><br/>')
    html = html.replace('<p>', '').replace('</p>', '<br/>')
    
    # Blockquotes
    html = html.replace('<blockquote>', '<i>"').replace('</blockquote>', '"</i>')
    
    return html


class ArticuloPDFGenerator:
    """Generador de PDFs para artículos científicos"""
    
    def __init__(self, articulo_data, noticias_referencias, plantilla='janus'):
        self.articulo = articulo_data
        self.referencias = noticias_referencias
        self.plantilla = plantilla
        self.story = []
        self.styles = self._crear_estilos()
    
    def _crear_estilos(self):
        """Crear estilos personalizados para el documento"""
        styles = getSampleStyleSheet()
        
        # Estilo para título principal
        styles.add(ParagraphStyle(
            name='TituloArticulo',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=28
        ))
        
        # Estilo para subtítulo
        styles.add(ParagraphStyle(
            name='SubtituloArticulo',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#4a4a4a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique',
            leading=20
        ))
        
        # Estilo para autores
        styles.add(ParagraphStyle(
            name='Autores',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#2a2a2a'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para afiliaciones
        styles.add(ParagraphStyle(
            name='Afiliacion',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))
        
        # Estilo para sección (Resumen, Abstract, etc.)
        styles.add(ParagraphStyle(
            name='SeccionTitulo',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            textTransform='uppercase'
        ))
        
        # Estilo para cuerpo de texto justificado
        styles.add(ParagraphStyle(
            name='CuerpoJustificado',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1a1a1a'),
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leading=16,
            fontName='Times-Roman'
        ))
        
        # Estilo para palabras clave
        styles.add(ParagraphStyle(
            name='PalabrasClave',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4a4a4a'),
            spaceAfter=12,
            fontName='Times-Italic'
        ))
        
        # Estilo para títulos de secciones del cuerpo
        styles.add(ParagraphStyle(
            name='TituloSeccionCuerpo',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=10,
            spaceBefore=16,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para referencias bibliográficas
        styles.add(ParagraphStyle(
            name='Referencia',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2a2a2a'),
            spaceAfter=4,
            leftIndent=20,
            firstLineIndent=-20,
            fontName='Times-Roman',
            leading=13
        ))
        
        return styles
    
    def _agregar_portada(self):
        """Generar portada del artículo (estilo JANUS/JSTOR)"""
        # Espacio superior
        self.story.append(Spacer(1, 1.5*cm))
        
        # Logo institucional (si existe)
        if self.articulo.get('logo_institucional'):
            try:
                logo = Image(self.articulo['logo_institucional'], width=3*cm, height=3*cm)
                logo.hAlign = 'CENTER'
                self.story.append(logo)
                self.story.append(Spacer(1, 0.5*cm))
            except:
                pass
        
        # Título
        titulo = Paragraph(self.articulo['titulo'].upper(), self.styles['TituloArticulo'])
        self.story.append(titulo)
        
        # Subtítulo (si existe)
        if self.articulo.get('subtitulo'):
            subtitulo = Paragraph(self.articulo['subtitulo'], self.styles['SubtituloArticulo'])
            self.story.append(subtitulo)
        
        self.story.append(Spacer(1, 0.8*cm))
        
        # Autores y afiliaciones
        autores = self.articulo.get('autores', [])
        if isinstance(autores, str):
            try:
                autores = json.loads(autores)
            except:
                autores = []
        
        for autor in autores:
            # Si autor es string, convertirlo a dict
            if isinstance(autor, str):
                autor = {'nombre': autor}
            
            nombre = Paragraph(autor.get('nombre', '') if isinstance(autor, dict) else str(autor), self.styles['Autores'])
            self.story.append(nombre)
            
            if isinstance(autor, dict) and autor.get('afiliacion'):
                afiliacion = Paragraph(autor['afiliacion'], self.styles['Afiliacion'])
                self.story.append(afiliacion)
            
            if isinstance(autor, dict) and autor.get('email'):
                email = Paragraph(f"<i>{autor['email']}</i>", self.styles['Afiliacion'])
                self.story.append(email)
        
        # Fecha
        fecha = self.articulo.get('fecha_creacion', datetime.now().strftime('%Y-%m-%d'))
        fecha_texto = Paragraph(f"<i>Fecha: {fecha}</i>", self.styles['Afiliacion'])
        self.story.append(Spacer(1, 0.5*cm))
        self.story.append(fecha_texto)
        
        # Salto de sección
        self.story.append(Spacer(1, 1*cm))
    
    def _agregar_resumen(self):
        """Agregar resumen y abstract bilingües"""
        # Resumen en español
        if self.articulo.get('resumen_es'):
            titulo_resumen = Paragraph('<b>RESUMEN</b>', self.styles['SeccionTitulo'])
            self.story.append(titulo_resumen)
            
            resumen_texto = Paragraph(self.articulo['resumen_es'], self.styles['CuerpoJustificado'])
            self.story.append(resumen_texto)
            
            # Palabras clave
            if self.articulo.get('palabras_clave'):
                palabras = ', '.join(self.articulo['palabras_clave'])
                pc_texto = Paragraph(f"<b>Palabras clave:</b> {palabras}", self.styles['PalabrasClave'])
                self.story.append(pc_texto)
            
            self.story.append(Spacer(1, 0.5*cm))
        
        # Abstract en inglés
        if self.articulo.get('abstract_en'):
            titulo_abstract = Paragraph('<b>ABSTRACT</b>', self.styles['SeccionTitulo'])
            self.story.append(titulo_abstract)
            
            abstract_texto = Paragraph(self.articulo['abstract_en'], self.styles['CuerpoJustificado'])
            self.story.append(abstract_texto)
            
            # Keywords
            if self.articulo.get('keywords'):
                keywords = ', '.join(self.articulo['keywords'])
                kw_texto = Paragraph(f"<b>Keywords:</b> {keywords}", self.styles['PalabrasClave'])
                self.story.append(kw_texto)
            
            self.story.append(Spacer(1, 0.8*cm))
    
    def _agregar_contenido(self):
        """Agregar secciones del cuerpo del artículo"""
        contenido_json = self.articulo.get('contenido_json', {})
        secciones = contenido_json.get('secciones', [])
        
        for seccion in secciones:
            # Manejar ambos formatos: editor nuevo (tipo, contenido_html) y viejo (titulo, orden)
            if 'tipo' in seccion:
                # Formato del editor: tipo es el nombre de la sección
                titulo = seccion.get('tipo', 'Sin título').replace('_', ' ').title()
            else:
                # Formato viejo
                titulo = seccion.get('titulo', 'Sin título')
            
            # Título de la sección
            titulo_seccion = Paragraph(titulo, self.styles['TituloSeccionCuerpo'])
            self.story.append(titulo_seccion)
            
            # Contenido HTML convertido
            contenido_html = seccion.get('contenido_html', '')
            contenido_limpio = html_to_reportlab(contenido_html)
            
            if contenido_limpio:
                parrafo = Paragraph(contenido_limpio, self.styles['CuerpoJustificado'])
                self.story.append(parrafo)
            
            self.story.append(Spacer(1, 0.3*cm))
    
    def _agregar_referencias(self):
        """Agregar lista de referencias bibliográficas"""
        if not self.referencias:
            return
        
        # Título de la sección
        titulo_refs = Paragraph('<b>REFERENCIAS BIBLIOGRÁFICAS</b>', self.styles['TituloSeccionCuerpo'])
        self.story.append(PageBreak())
        self.story.append(titulo_refs)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Formatear cada referencia según estilo
        estilo_citas = self.articulo.get('estilo_citas', 'chicago')
        
        for idx, ref in enumerate(self.referencias, 1):
            cita_formateada = self._formatear_cita(ref, idx, estilo_citas)
            ref_parrafo = Paragraph(cita_formateada, self.styles['Referencia'])
            self.story.append(ref_parrafo)
            self.story.append(Spacer(1, 0.2*cm))
    
    def _formatear_cita(self, referencia, numero, estilo):
        """
        Formatear referencia bibliográfica según estilo
        Estilos: chicago, apa, vancouver, mla
        """
        titulo = referencia.get('titulo', 'Sin título')
        autor = referencia.get('autor', 'Anónimo')
        medio = referencia.get('medio', '')
        fecha = referencia.get('fecha', '')
        url = referencia.get('url', '')
        
        if estilo == 'apa':
            # APA 7: Autor, A. A. (Año, Mes Día). Título del artículo. Nombre del Medio. URL
            return f"[{numero}] {autor}. ({fecha}). {titulo}. <i>{medio}</i>. {url}"
        
        elif estilo == 'vancouver':
            # Vancouver: Número. Autor. Título. Medio. Fecha; URL
            return f"{numero}. {autor}. {titulo}. {medio}. {fecha}; Disponible en: {url}"
        
        elif estilo == 'mla':
            # MLA: Autor. "Título del Artículo." Medio, Fecha, URL
            return f'{autor}. "{titulo}." <i>{medio}</i>, {fecha}, {url}'
        
        else:  # chicago (default)
            # Chicago: Autor. "Título del Artículo." Medio, Fecha. URL
            return f'[{numero}] {autor}. "{titulo}." <i>{medio}</i>, {fecha}. {url}'
    
    def generar_pdf(self, output_path=None):
        """
        Generar el PDF completo
        Retorna BytesIO si no se especifica output_path
        """
        # Determinar output
        if output_path:
            buffer = output_path
        else:
            buffer = BytesIO()
        
        # Configurar documento
        if self.plantilla == 'janus':
            pagesize = A4
            margin = 2.5*cm
        elif self.plantilla == 'jstor':
            pagesize = letter
            margin = 1*inch
        else:  # apa
            pagesize = letter
            margin = 1*inch
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesize,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
            title=self.articulo['titulo'],
            author=', '.join([a.get('nombre', '') for a in self.articulo.get('autores', [])])
        )
        
        # Construir contenido
        self._agregar_portada()
        self._agregar_resumen()
        self._agregar_contenido()
        self._agregar_referencias()
        
        # Generar PDF con numeración de páginas
        doc.build(self.story, onFirstPage=self._agregar_encabezado_pie, 
                  onLaterPages=self._agregar_encabezado_pie)
        
        if not output_path:
            buffer.seek(0)
            return buffer
    
    def _agregar_encabezado_pie(self, canvas, doc):
        """Agregar encabezado y pie de página con numeración"""
        canvas.saveState()
        
        # Encabezado (solo en páginas > 1)
        if doc.page > 1:
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(colors.HexColor('#666666'))
            # Título corto del artículo (primeras 60 caracteres)
            titulo_corto = self.articulo['titulo'][:60] + '...' if len(self.articulo['titulo']) > 60 else self.articulo['titulo']
            canvas.drawString(doc.leftMargin, doc.height + doc.topMargin - 0.5*cm, titulo_corto)
        
        # Pie de página con número
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawCentredString(doc.width/2 + doc.leftMargin, 1.5*cm, f"Página {doc.page}")
        
        canvas.restoreState()


def generar_pdf_articulo(articulo_data, noticias_referencias, plantilla='janus'):
    """
    Función auxiliar para generar PDF de artículo
    
    Args:
        articulo_data: Diccionario con datos del artículo
        noticias_referencias: Lista de noticias citadas
        plantilla: 'janus', 'jstor' o 'apa'
    
    Returns:
        BytesIO con el PDF generado
    """
    generador = ArticuloPDFGenerator(articulo_data, noticias_referencias, plantilla)
    return generador.generar_pdf()

class NoticiaPDFGenerator:
    """Generador de PDFs para noticias individuales (Prensa) - Estilo Académico"""
    
    def __init__(self, noticia_data):
        self.noticia = noticia_data
        self.story = []
        self.styles = self._crear_estilos()
    
    def _crear_estilos(self):
        """Crear estilos personalizados para la noticia (Estilo Académico)"""
        styles = getSampleStyleSheet()
        
        # Título Principal (Serif, Grande, Centrado)
        styles.add(ParagraphStyle(
            name='TituloNoticia',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#000000'),
            spaceAfter=18,
            alignment=TA_CENTER,
            fontName='Times-Bold',
            leading=26
        ))
        
        # Metadatos (Serif, Limpio)
        styles.add(ParagraphStyle(
            name='Metadatos',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2c2c2c'),
            spaceAfter=8,
            alignment=TA_LEFT,
            fontName='Times-Roman',
            leading=14
        ))
        
        # Claves de Metadatos (Negrita)
        styles.add(ParagraphStyle(
            name='MetadatosLabel',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            alignment=TA_RIGHT,
            fontName='Times-Bold',
            leading=14
        ))
        
        # Cuerpo (Times New Roman, Justificado, Académico)
        styles.add(ParagraphStyle(
            name='CuerpoNoticia',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#000000'),
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=18,  # Mayor interlineado para lectura
            fontName='Times-Roman',
            firstLineIndent=20  # Indentación de párrafo clásica
        ))
        
        # Notas (Menor tamaño, cursiva opcional)
        styles.add(ParagraphStyle(
            name='NotasNoticia',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=15,
            fontName='Times-Italic'
        ))
        
        # Títulos de Sección (Subtítulos)
        styles.add(ParagraphStyle(
            name='SeccionTitulo',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#000000'),
            spaceBefore=18,
            spaceAfter=10,
            fontName='Times-Bold',
            borderPadding=4,
            borderWidth=0,
            borderColor=colors.HexColor('#000000')
        ))
        
        return styles
    
    def generar_pdf(self):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2.5*cm,
            rightMargin=2.5*cm,
            topMargin=3*cm,  # Margen superior para encabezado
            bottomMargin=3*cm, # Margen inferior para pie
            title=self.noticia.get('titulo', 'Noticia')
        )
        
        # --- 1. Encabezado Institucional / Título ---
        titulo = self.noticia.get('titulo', 'Sin Título')
        self.story.append(Paragraph(titulo, self.styles['TituloNoticia']))
        
        # Línea separadora decorativa
        self.story.append(Spacer(1, 0.2*cm))
        
        # --- 2. Tabla de Metadatos (Diseño Refinado) ---
        # Formato: Etiqueta | Valor
        data = [
            [Paragraph('Autor/a:', self.styles['MetadatosLabel']), Paragraph(self.noticia.get('autor', 'Desconocido'), self.styles['Metadatos'])],
            [Paragraph('Publicación:', self.styles['MetadatosLabel']), Paragraph(f"{self.noticia.get('publicacion', '')} {self.noticia.get('descripcion_publicacion', '')}", self.styles['Metadatos'])],
            [Paragraph('Fecha:', self.styles['MetadatosLabel']), Paragraph(self.noticia.get('fecha_original', ''), self.styles['Metadatos'])],
            [Paragraph('Ubicación:', self.styles['MetadatosLabel']), Paragraph(f"{self.noticia.get('ciudad', '')}", self.styles['Metadatos'])],
            [Paragraph('Detalles:', self.styles['MetadatosLabel']), Paragraph(f"Núm. {self.noticia.get('numero', '-')} | Págs. {self.noticia.get('paginas', '-')}", self.styles['Metadatos'])],
            [Paragraph('Temas:', self.styles['MetadatosLabel']), Paragraph(self.noticia.get('temas', ''), self.styles['Metadatos'])]
        ]
        
        # Filtrar filas vacías (donde el valor está vacío)
        data = [row for row in data if row[1].text and row[1].text != '']
        
        if data:
            t = Table(data, colWidths=[4*cm, 12*cm])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')), # Líneas sutiles entre filas
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
            ]))
            self.story.append(t)
            self.story.append(Spacer(1, 1.5*cm))
        
        # --- 3. Contenido Principal ---
        contenido = self.noticia.get('contenido', '')
        if contenido:
            # Título de sección con estilo
            self.story.append(Paragraph("TRANSCRIPCIÓN DEL DOCUMENTO", self.styles['SeccionTitulo']))
            
            # Línea fina debajo del título de sección
            # self.story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
            
            if '<p>' in contenido or '<br>' in contenido:
                contenido_fmt = html_to_reportlab(contenido)
            else:
                contenido_fmt = contenido.replace('\n', '<br/>')
            
            self.story.append(Paragraph(contenido_fmt, self.styles['CuerpoNoticia']))
            self.story.append(Spacer(1, 1*cm))
            
        # --- 4. Notas y Observaciones ---
        notas = self.noticia.get('notas', '')
        if notas:
            self.story.append(Paragraph("NOTAS Y OBSERVACIONES", self.styles['SeccionTitulo']))
            
            if '<p>' in notas or '<br>' in notas:
                notas_fmt = html_to_reportlab(notas)
            else:
                notas_fmt = notas.replace('\n', '<br/>')
                
            self.story.append(Paragraph(notas_fmt, self.styles['NotasNoticia']))
            
        # Build con encabezados y pies de página
        doc.build(self.story, onFirstPage=self._agregar_encabezado_pie, onLaterPages=self._agregar_encabezado_pie)
        buffer.seek(0)
        return buffer

    def _agregar_encabezado_pie(self, canvas, doc):
        """Agregar encabezado y pie de página profesional con datos del proyecto y la noticia"""
        canvas.saveState()
        
        # Intentar obtener datos del contexto Flask (Proyecto y Usuario)
        proyecto_nombre = "PROYECTO SIRIO - HEMEROTECA DIGITAL"
        proyecto_desc = ""
        usuario_nombre = ""
        
        try:
            from utils import get_proyecto_activo
            from flask_login import current_user
            
            p = get_proyecto_activo()
            if p:
                proyecto_nombre = p.nombre.upper()
                proyecto_desc = p.descripcion or ""
            
            if current_user and current_user.is_authenticated:
                usuario_nombre = f" | Usuario: {current_user.nombre}"
                
        except Exception:
            pass

        # Datos de la Noticia para el encabezado
        pub_nombre = self.noticia.get('publicacion') or ""
        fecha_orig = self.noticia.get('fecha_original') or ""
        header_center = f"{pub_nombre}  •  {fecha_orig}" if (pub_nombre and fecha_orig) else (pub_nombre or fecha_orig)

        # --- Encabezado ---
        # 1. Nombre del Proyecto (Izquierda Superior)
        canvas.setFont('Times-Bold', 10)
        canvas.setFillColor(colors.HexColor('#000000'))
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin + 1.2*cm, proyecto_nombre)
        
        # 2. Descripción del Proyecto (Izquierda Inferior, pequeño)
        if proyecto_desc:
            canvas.setFont('Times-Italic', 8)
            canvas.setFillColor(colors.HexColor('#666666'))
            desc_corta = (proyecto_desc[:60] + '...') if len(proyecto_desc) > 60 else proyecto_desc
            canvas.drawString(doc.leftMargin, doc.height + doc.topMargin + 0.8*cm, desc_corta)

        # 3. Publicación y Fecha (Centro - Estilo Periódico)
        if header_center:
            canvas.setFont('Times-BoldItalic', 11)
            canvas.setFillColor(colors.HexColor('#2c3e50'))
            canvas.drawCentredString(doc.width/2 + doc.leftMargin, doc.height + doc.topMargin + 1.0*cm, header_center)

        # 4. Metadatos de Impresión (Derecha)
        fecha_impresion = datetime.now().strftime("%d/%m/%Y %H:%M")
        canvas.setFont('Times-Roman', 8)
        canvas.setFillColor(colors.HexColor('#444444'))
        
        info_impresion = f"Impreso: {fecha_impresion}"
        canvas.drawRightString(doc.width + doc.leftMargin, doc.height + doc.topMargin + 1.2*cm, info_impresion)
        if usuario_nombre:
             canvas.drawRightString(doc.width + doc.leftMargin, doc.height + doc.topMargin + 0.8*cm, usuario_nombre.replace(" | ", ""))
        
        # Línea divisoria encabezado (Doble línea para estilo académico)
        canvas.setStrokeColor(colors.HexColor('#000000'))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, doc.height + doc.topMargin + 0.5*cm, doc.width + doc.leftMargin, doc.height + doc.topMargin + 0.5*cm)
        canvas.setLineWidth(0.2)
        canvas.line(doc.leftMargin, doc.height + doc.topMargin + 0.45*cm, doc.width + doc.leftMargin, doc.height + doc.topMargin + 0.45*cm)
        
        # --- Pie de página ---
        # Línea divisoria pie
        canvas.setStrokeColor(colors.HexColor('#cccccc'))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 1.8*cm, doc.width + doc.leftMargin, 1.8*cm)
        
        # Centro: Número de página
        canvas.setFont('Times-Roman', 9)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawCentredString(doc.width/2 + doc.leftMargin, 1.2*cm, f"Página {doc.page} - Generado por Sirio Hemeroteca")
        
        canvas.restoreState()

def generar_pdf_noticia_simple(noticia_data):
    """Wrapper para generar PDF de noticia"""
    generador = NoticiaPDFGenerator(noticia_data)
    return generador.generar_pdf()
