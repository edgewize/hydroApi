from hydroApp import db

class Screenshot(db.Model):
    __tablename__ = "screenshots"
    __table_args__ = {'extend_existing': True}
    timestamp = db.Column("timestamp", db.DateTime, primary_key=True, nullable=False)
    url = db.Column("url", db.String(100), nullable=False)
    count = db.Column("count", db.Integer)
    test_count = db.Column("test_count", db.Integer)

    def __init__(self, timestamp, url, count, test_count):
        self.timestamp = timestamp
        self.url = url
        self.count = count
        self.test_count = test_count


if __name__ == "__main__":
    from run import app
    # Run this file directly to create the database tables.
    print("Creating database tables...")
    with app.app_context():
        # db.session.remove()
        db.drop_all()
        # db.drop_database()
        db.create_all()

    print("Done!")