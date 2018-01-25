from flask import render_template
import json
from cs50 import SQL

def apology(message, code=400):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def check_money(recipient_fb_id, db):
    rows = db.execute("SELECT * FROM users WHERE recipient_fb_id = :recipient_fb_id", recipient_fb_id=recipient_fb_id)
    # if not rows[0]:
    #     return None
    user_id = rows[0]['user_id']
    rows = db.execute("SELECT * FROM records WHERE customer_id = :customer_id", customer_id=user_id)
    total_money = 0
    for row in rows:
        total_money += row["amount"]
    return total_money
