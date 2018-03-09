from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Catalog, Base, Item, User

engine = create_engine('sqlite:///catalogwithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="user1", email="mluc.utexas@gmail.com")
session.add(User1)
session.commit()

catalog1 = Catalog(user_id=1, name="Soccer")
session.add(catalog1)
session.commit()

item1 = Item(user_id=1, name="Two shinguards",
             description="adidas Youth Ghost Shin GuardsStay Aggressive. Play Inspired.With a pair of adidas Youth Ghost Shin Guards, your young soccer star can stay in the middle ofA the action whileA challenging for control of the soccer ball. These colorful soccer shin guards feature a strap system to keep them in place. With a hard front plate, built-in ankle guard and cushioned back providing superior protection and impact absorption, they can stay on the attack and maintain their focus when the action heats up.adidas Youth Ghost Shin Guards feature: * Highly protective hard front plate * Single-strap front closure with attached ankle guard for more protection * EVA backing for comfort and durable cushioning * 95% Polypropylene, 5% Thermoplastic gum, injection molded.",
             catalog=catalog1)
session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Soccer Cleats",
             description="Classic looks and all-game comfort are what these juniors' Soccer cleats are all about. They feature a lightweight, durable synthetic upper. Designed for stability and speed on firm ground.",
             catalog=catalog1)
session.add(item2)
session.commit()

item3 = Item(user_id=1, name="Jersey",
             description="URBANCREWS by MKS America Inc. One stop street-wear hip hop fashion destination.",
             catalog=catalog1)
session.add(item3)
session.commit()

catalog2 = Catalog(user_id=1, name="Snowboarding")
session.add(catalog2)
session.commit()

item1 = Item(user_id=1, name="Goggles",
            description="Inspired by the helmet visors of fighter pilots, Flight Deck maximizes your field of view so you won't miss a single target of opportunity. Peripheral and downward vision are wide open for spotting challenges and dangers and the interchangeable lens system lets you adapt to whatever the sky dishes out. The rimless design has wide-ranging helmet compatibility plus the comfort of minimized frame mass and it meets ANSI Z87.1 standards for impact resistance. With clean style and a field of view that's unparalleled, this is the ace of snow goggles.",
            catalog=catalog2)
session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Snowboard",
             description="Northern Ridge brings you the Beginner Plastic Snowboard, perfect for introducing your kids to snowboarding right in your own backyard. + Rugged Plastic Construction with no metal edges + Traditional Snowboard Shape + Adjustable, Cinch Bindings + Bindings come pre-mounted and can be reversed for switch riders + Approx 43in long / 4 LBs + Recommended for ages 9 and up + Not intended for mountain or resort use.",
             catalog=catalog2)
session.add(item2)
session.commit()