import psycopg2
from psycopg2 import sql
import bcrypt

DB_CONFIG = {
    'database': 'sample2024',
    'user': 'db2024',
    'password': 'db!2024',
    'host': '::1',
    'port': '5432'
}

def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None


def initialize_tables():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(20) PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    user_role VARCHAR(20) DEFAULT 'user',
                    trust_score INT DEFAULT 0,
                    is_honored BOOLEAN DEFAULT FALSE,
                    reported INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS information(
                    info_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(20) REFERENCES users(user_id) ON DELETE CASCADE,
                    location VARCHAR(100) NOT NULL,
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL,
                    description VARCHAR(1000) NOT NULL,
                    people_count INT DEFAULT 0,
                    recommended INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
                );

                CREATE TABLE IF NOT EXISTS comment(
                    comment_id SERIAL PRIMARY KEY,
                    info_id SERIAL REFERENCES information(info_id) ON DELETE CASCADE,
                    user_id VARCHAR(20) REFERENCES users(user_id) ON DELETE CASCADE,
                    comment_content VARCHAR(100) NOT NULL,
                    recommended INT DEFAULT 0,
                    reported INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
                );

                CREATE TABLE IF NOT EXISTS announcement(
                    announcement_id SERIAL PRIMARY KEY,
                    admin_id VARCHAR(20) REFERENCES users(user_id) ON DELETE SET NULL,
                    title VARCHAR(100) NOT NULL,
                    content VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS analysis(
                    task SERIAL PRIMARY KEY,
                    analyst_id VARCHAR(20) REFERENCES users(user_id) ON DELETE SET NULL,
                    title VARCHAR(100) NOT NULL,
                    content VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE OR REPLACE VIEW post_view AS
                SELECT 
                    i.info_id, 
                    i.user_id AS info_user_id, 
                    i.location, 
                    i.description, 
                    i.recommended, 
                    i.created_at AS info_created_at, 
                    u.is_honored
                FROM 
                    information i
                LEFT JOIN 
                    users u ON i.user_id = u.user_id
                
            """)
            cursor.execute("""
                            CREATE OR REPLACE VIEW announcement_view AS
                            SELECT * FROM announcement
                        """)

            cursor.execute("""
                            CREATE OR REPLACE VIEW analysis_view AS
                            SELECT * FROM analysis
                        """)

            cursor.execute("""
                CREATE OR REPLACE VIEW user_info_view AS
                SELECT 
                    user_id, 
                    email, 
                    trust_score, 
                    is_honored, 
                    reported 
                FROM 
                    users;
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_trust_score ON users(trust_score DESC);
                CREATE INDEX IF NOT EXISTS idx_users_reported ON users(reported DESC);
            """)

            # 기본 사용자 데이터 삽입
            admin_password = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            analyst_password = bcrypt.hashpw("analyst".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            cursor.execute("""
                INSERT INTO users (user_id, username, password, email, user_role) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING;
            """, ('admin', 'admin', admin_password, 'admin@example.com', 'admin'))

            cursor.execute("""
                INSERT INTO users (user_id, username, password, email, user_role) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING;
            """, ('analyst', 'analyst', analyst_password, 'analyst@example.com', 'analyst'))

            conn.commit()
            print("Tables, Views, and Indexes initialized successfully!")
        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
