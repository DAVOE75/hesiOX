import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailService:
    @staticmethod
    def send_newsletter(subscribers, post):
        """
        Envía un correo electrónico a una lista de suscriptores con el contenido de un post.
        """
        # Configuración desde variables de entorno
        mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
        mail_port = int(os.getenv("MAIL_PORT", 587))
        mail_user = os.getenv("MAIL_USERNAME")
        mail_pass = os.getenv("MAIL_PASSWORD")
        mail_sender = os.getenv("MAIL_DEFAULT_SENDER", mail_user)
        
        if not mail_user or not mail_pass:
            print("[ERROR] No se han configurado las credenciales de correo (MAIL_USERNAME/MAIL_PASSWORD).")
            return False, "Credenciales no configuradas"

        success_count = 0
        error_count = 0
        
        try:
            # Conexión al servidor
            server = smtplib.SMTP(mail_server, mail_port)
            server.starttls()
            server.login(mail_user, mail_pass)
            
            for sub in subscribers:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = f"Nuevo en el Blog de HesiOX: {post.titulo}"
                    msg['From'] = f"HesiOX <{mail_sender}>"
                    msg['To'] = sub.email
                    
                    # Versión HTML
                    html_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 10px; overflow: hidden;">
                            <div style="background-color: #1a1a1a; padding: 20px; text-align: center;">
                                <h1 style="color: #ff9800; margin: 0;">HesiOX</h1>
                            </div>
                            <div style="padding: 30px;">
                                <h2 style="color: #1a1a1a;">{post.titulo}</h2>
                                <p style="color: #666; font-size: 0.9rem;">{post.publicado_en.strftime('%d/%m/%Y') if post.publicado_en else ''}</p>
                                <hr style="border: 0; border-top: 1px solid #eee;">
                                <div style="margin: 20px 0;">
                                    {post.get_resumen_corto(300)}
                                </div>
                                <div style="text-align: center; margin-top: 30px;">
                                    <a href="https://hesiox.es/blog/{post.slug}" 
                                       style="background-color: #ff9800; color: #fff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                                       Leer artículo completo
                                    </a>
                                </div>
                            </div>
                            <div style="background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 0.8rem; color: #888;">
                                <p>© {datetime.now().year} Proyecto HesiOX - Humanidades Digitales</p>
                                <p>Recibes este correo porque estás suscrito al blog de HesiOX.</p>
                                <p><a href="https://hesiox.es/blog/unsubscribe?email={sub.email}" style="color: #888;">Darse de baja</a></p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    part2 = MIMEText(html_content, 'html')
                    msg.attach(part2)
                    
                    server.sendmail(mail_sender, sub.email, msg.as_string())
                    success_count += 1
                except Exception as e:
                    print(f"[ERROR] Error enviando a {sub.email}: {e}")
                    error_count += 1
                    
            server.quit()
            return True, f"Enviados: {success_count}, Errores: {error_count}"
            
        except Exception as e:
            print(f"[ERROR] Error de conexión SMTP: {e}")
            return False, str(e)
