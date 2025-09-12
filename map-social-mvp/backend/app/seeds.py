from sqlmodel import Session
from .db import engine, init_db
from .models import User, Location, Post, Comment, SessionEvent
from .deps import hash_password
from datetime import datetime, timedelta

def run():
    init_db()
    with Session(engine) as s:
        # Users
        if not s.get(User, 1):
            alice = User(email="alice@example.com", display_name="Alice", hashed_password=hash_password("alicepw"))
            bob = User(email="bob@example.com", display_name="Bob", hashed_password=hash_password("bobpw"))
            s.add(alice); s.add(bob); s.commit()
        else:
            alice = s.get(User, 1); bob = s.get(User, 2)

        # Locations (DMV sample)
        locs = [
            Location(title="Earth Treks Rockville", kind="climbing_gym", lat=39.085, lon=-77.164, address="725 Rockville Pike, Rockville, MD"),
            Location(title="C&O Canal Towpath – Carderock", kind="running_route", lat=38.972, lon=-77.200, address="Carderock, MD"),
            Location(title="Whitetail Resort", kind="ski_resort", lat=39.613, lon=-77.934, address="Mercersburg, PA"),
            Location(title="Seneca Creek State Park – Lake Shore Trail", kind="hiking_route", lat=39.142, lon=-77.236, address="Gaithersburg, MD"),
            Location(title="Founding Farmers Tysons", kind="restaurant", lat=38.924, lon=-77.224, address="Tysons, VA"),
        ]
        for L in locs:
            s.add(L)
        s.commit()

        # Posts
        L1 = s.exec(s.query(Location).filter(Location.title == "Earth Treks Rockville")).first()
        if L1:
            p1 = Post(location_id=L1.id, author_id=alice.id, content="Looking for bouldering partners Sat morning, V2–V4.", tags="bouldering,partner")
            p2 = Post(location_id=L1.id, author_id=bob.id, content="New to lead climbing. Anyone up for 5.9 routes tonight?", tags="lead,partner")
            s.add(p1); s.add(p2); s.commit()
            c1 = Comment(post_id=p1.id, author_id=bob.id, content="I'm in! 10am?")
            s.add(c1); s.commit()

        # Session demo
        if L1:
            se = SessionEvent(
                location_id=L1.id,
                host_id=alice.id,
                title="Saturday Bouldering Jam",
                activity="bouldering",
                starts_at=datetime.utcnow() + timedelta(days=2, hours=10),
                ends_at=datetime.utcnow() + timedelta(days=2, hours=12),
                max_people=6,
                notes="Warm-up V1, project V4"
            )
            s.add(se); s.commit()

    print("Seeded! Users: alice@example.com/alicepw, bob@example.com/bobpw")

if __name__ == "__main__":
    run()
