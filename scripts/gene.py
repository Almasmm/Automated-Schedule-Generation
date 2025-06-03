from dataclasses import dataclass

@dataclass
class Gene:
    group: str
    course: str
    type: str  # "Lecture", "Practice", "Lab"
    day: str
    time: str  # e.g. "08:00"
    room: str
    instructor: str = None  # optional, manually assigned
    delivery_mode: str = "offline"  # "offline" or "online"

    def to_dict(self):
        """Return dictionary format for JSON export"""
        return {
            "group": self.group,
            "course": self.course,
            "type": self.type,
            "day": self.day,
            "time": self.time,
            "room": self.room,
            "instructor": self.instructor or "TBD",
            "delivery_mode": self.delivery_mode
        }

    def __str__(self):
        return (f"{self.day} {self.time} | {self.course:25} | {self.type:<8} | "
                f"{self.room:<10} | {self.delivery_mode:<7} | {self.instructor or 'TBD'}")
