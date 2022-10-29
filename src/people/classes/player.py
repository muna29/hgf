import math, os, random, uuid, pickle
from random import randint

from src.lifesim_lib.const import *
from src.lifesim_lib.translation import _
from src.lifesim_lib.lifesim_lib import *
from src.people.classes.parent import Parent
from src.people.classes.person import Person
from src.people.classes.sibling import Sibling
from src.people.classes.partner import Partner


class Player(Person):
    """Base class for the player."""

    def __init__(self, first=None, last=None, gender=None):
        gender = gender or Gender.random()
        first = first or random_name(gender)
        last = last or random.choice(LAST_NAMES)
        happiness = randint(50, 100)
        health = randint(75, 100)
        smarts = randint(0, 50) + randint(0, 50)
        looks = randint(0, 65) + randint(0, 35)
        super().__init__(first, last, 0, gender, happiness, health, smarts, looks)
        last1 = last2 = last
        if randint(1, 100) <= 40:
            newlast = random_last_name()
            if random.randint(1, 3) == 1:
                last2 = newlast  # Makes it more common to be named after the father's last name
            else:
                last1 = newlast
        self.parents = {
            "Mother": Parent(
                last1,
                min(randint(randint(18, 20), 50) for _ in range(3)),
                Gender.Female,
            ),
            "Father": Parent(
                last2, min(randint(randint(18, 20), 68) for _ in range(3)), Gender.Male
            ),
        }
        diff = self.parents["Father"].generosity - self.parents["Mother"].generosity
        if randint(1, 2) == 1:
            if diff > 0:
                self.parents["Mother"].generosity += randint(0, diff // 2)
            elif diff < 0:
                self.parents["Mother"].generosity -= randint(0, abs(diff) // 2)
        else:
            diff = -diff
            if diff > 0:
                self.parents["Father"].generosity += randint(0, diff // 2)
            elif diff < 0:
                self.parents["Father"].generosity -= randint(0, abs(diff) // 2)

        self.relations = [self.parents["Mother"], self.parents["Father"]]

        self.karma = randint(0, 25) + randint(0, 25) + randint(0, 25) + randint(0, 25)
        self.total_happiness = 0
        self.meditated = False
        self.worked_out = False
        self.money = 0
        self.depressed = False
        self.student_loan = 0
        self.chose_student_loan = False
        self.uv_years = 0
        self.reset_already_did()
        self.grades = None
        self.dropped_out = False
        self.times_meditated = 0
        self.salary = 0
        self.years_worked = 0
        self.has_job = False
        self.lottery_jackpot = 0
        self.stress = 0
        self.performance = 0
        self.job_hours = 40
        self.date_options = 10
        self.times_visited_library = 0
        self.times_asked_since_last_raise = 0
        self.last_raise = 0
        self.partner = None
        self.traits = {}
        self.illnesses = []
        self.salary_years = []
        self.ID = str(uuid.uuid4())
        self.save_path = SAVE_PATH + "/" + self.ID + ".pickle"

    def learn_trait(self, trait):
        if trait not in TRAITS_DICT:
            return False
        if self.has_trait(trait):
            return False
        conflicts = [
            t
            for t in self.traits.values()
            if (t.id != trait and t.conflicts_with(trait))
        ]
        if conflicts:
            removal = random.choice(conflicts)
            color = None
            if removal.val > 0:
                color = "red"  # Losing a good trait is bad
            elif removal.val < 0:
                color = "green"  # Losing a bad trait is good
            print_colored(
                _("You lose the {trait!r} trait!").format(trait=removal.name), color
            )
            del self.traits[removal.id]
        else:
            data = ALL_TRAITS_DICT[trait]
            data.get_color()
            print_colored(
                _("You have gained the {trait} trait!").format(trait=data.name),
                data.get_color(),
            )
            self.traits[trait] = data
        return True

    def is_depressed(self):
        return (
            "Depression" in self.illnesses
        )  # TODO: Migrate depression to a list of diseases

    def generate_partner(self):
        m = self.age // 6
        age = 0
        while age < 18:
            age = self.age + randint(-m, m)
        gender = Gender.Female if self.gender == Gender.Male else Gender.Male
        p = Partner(
            age,
            gender,
            randint(0, 50) + randint(0, 50),
            randint(0, 60) + randint(0, 40),
            50,
            0,
        )
        while p.death_check():
            p.age -= randint(1, 5)
        return p

    def has_trait(self, name):
        return name in self.traits

    def was_attacked(self, damage, can_die=True):
        self.change_happiness(damage)
        self.change_health(damage)
        if damage >= 40:
            self.change_looks(-randint(0, (damage - 40) // 2))
        if self.can_die and self.health <= 0 and randint(1, 100) <= damage:
            self.die(_("You died after sustaining massive injuries in an assault."))

    def randomize_traits(self):
        self.traits.clear()
        trait_names = list(ALL_TRAITS_DICT.keys())
        total_traits = len(ALL_TRAITS)
        num_traits = 1
        while randint(1, 100) <= 40 and num_traits < randint(1, total_traits):
            num_traits += 1
        t = {}
        for i in range(num_traits):
            attempts = 50
            good = randint(1, 100) <= 60
            while attempts > 0:
                name = random.choice(trait_names)
                if name in t:
                    attempts -= 1
                    continue
                selected = ALL_TRAITS_DICT[name]
                if selected.val != 0 and (selected.val > 0) ^ good:
                    attempts -= 1
                    continue
                if not selected.roll_selection():
                    continue
                if len(t) < 1 or not any(selected.conflicts_with(trait) for trait in t):
                    break
                else:
                    attempts -= 1
            if attempts > 0:
                t[name] = selected
        self.traits = t

    def after_trait_select(self):
        if self.has_trait("GRUMPY"):
            self.change_happiness(-12)

    def print_traits(self):
        if self.traits:
            print()
            print(_("You have the following traits:"))
            for name in self.traits:
                trait = self.traits[name]
                print_colored(f"{trait.name}: {trait.desc}", trait.get_color())

    @classmethod
    def load(cls, d):
        p = cls()
        p.__dict__.update(d)
        return p

    def change_happiness(self, amount):
        if amount != 0 and self.has_trait("MOODY"):
            amount = round_stochastic(amount * 1.5)
        super().change_happiness(amount)

    def change_jackpot(self):
        self.lottery_jackpot = round(randexpo(100000, 1000000))

    def save_game(self):
        if not os.path.exists(self.save_path):
            open(self.save_path, "x")
        pickle.dump(self.__dict__, open(self.save_path, "wb"))

    def delete_save(self):
        if os.path.exists(self.save_path):
            os.remove(self.save_path)

    def is_in_school(self):
        return self.grades is not None

    def add_illness(self, illness):
        if illness not in self.illnesses:
            self.illnesses.append(illness)

    def remove_illness(self, illness):
        if illness in self.illnesses:
            self.illnesses.remove(illness)

    def change_grades(self, amount):
        if self.is_in_school():
            self.grades = clamp(self.grades + amount, 0, 100)

    def change_karma(self, amount):
        self.karma = clamp(self.karma + amount, 0, 100)

    def get_traits_str(self):
        return ", ".join(
            map(lambda t: get_colored(t.name, t.get_color()), self.traits.values())
        )

    def reset_already_did(self):
        self.meditated = False
        self.worked_out = False
        self.visited_library = False
        self.studied = False
        self.tried_to_drop_out = False
        self.played = False
        self.did_arts_and_crafts = False
        self.worked_harder = False
        self.listened_to_music = False
        self.asked_for_raise = False
        self.date_options = randint(9, 11)

    def age_up(self):
        oldhappy = self.happiness
        self.total_happiness += self.happiness
        super().age_up()
        if self.has_trait("SICKLY"):
            self.change_health(-randint(0, 4))
        if self.has_trait("MOODY") and not self.is_depressed():
            self.change_happiness(randint(-8, 8))
        if self.has_trait("GRUMPY") and self.happiness > 33:
            if randint(1, 10) == 1:
                self.change_happiness(-randint(5, 8))
            else:
                self.change_happiness(-randint(1, 5))
        if self.has_trait("FAST_WORKER"):
            self.change_performance(randint(0, 3))
        elif self.has_trait("SLOW_WORKER"):
            self.change_performance(-randint(0, 3))
        if self.has_trait("LAZY"):
            self.change_performance(-randint(0, 5))
            self.change_stress(-randint(0, 4))
        self.reset_already_did()
        self.change_karma(randint(-2, 2))

        for relation in self.relations:
            relation.age_up()
            if isinstance(relation, Parent):
                if self.age < 18:
                    relation.change_relationship(1)
                else:
                    relation.change_relationship(random.choice((-1, -1, 0)))

        print(_("Age {age}").format(age=self.age))
        if self.death_check():
            self.die(_("You died of old age."))
            return
        self.change_jackpot()
        if self.has_job:
            self.change_stress(randint(-4, 4))
            base = 60 - self.happiness * 0.3 + (self.job_hours - 40)
            diff = base - self.stress
            if diff > 0:
                self.change_stress(randint(0, round_stochastic(diff / 6)))
            elif diff < 0:
                factor = self.happiness / 25 + 0.5
                self.change_stress(
                    -randint(0, round_stochastic(abs(diff) / 9 * factor))
                )
        if self.happiness < randint(1, 10) and not self.is_depressed():
            display_event(_("You are suffering from depression."))
            self.add_illness("Depression")
            self.change_happiness(-50)
            self.change_health(-randint(4, 8))
        for relation in self.relations[:]:
            if relation.death_check():
                rel_str = relation.name_accusative()
                print(
                    _(
                        "Your {relative} died at the age of {age} due to old age."
                    ).format(relative=rel_str, age=relation.age)
                )
                inheritance = 0
                happy_remove = randint(40, 55)
                if isinstance(relation, Parent):
                    if randint(1, 100) <= 70 and randint(1, 100) <= relation.generosity:
                        avg = 100000 * (relation.money / 100) ** 2
                        lo = max(avg * relation.generosity / 200, 1)
                        inheritance = round_stochastic(randexpo(lo, avg))
                    del self.parents[relation.get_type()]
                elif isinstance(relation, Sibling):
                    happy_remove = randint(25, 40)
                elif isinstance(relation, Partner):
                    happy_remove = randint(60, 100)
                    self.partner = None
                self.change_happiness(-happy_remove)
                if yes_no(_("Would you like to attend the funeral?")):
                    self.change_happiness(randint(3, 5))
                    self.change_karma(randint(3, 5))
                else:
                    self.change_karma(-randint(2, 5))
                self.relations.remove(relation)
                if inheritance > 0:
                    display_event(
                        _("You inherited ${amount}").format(amount=inheritance)
                    )
                    self.money += inheritance
                    self.change_happiness(
                        round_stochastic(1.5 * math.log10(inheritance))
                    )
        self.random_events()
        if self.partner:
            assert self.partner in self.relations
        if self.has_job:
            self.salary_years.append(self.salary)
            happy_change = (
                self.happiness - oldhappy
            )  # Large decreases in happiness can increase stress
            if happy_change > 0:
                diff = max(happy_change - 5, 0)
                diff /= 2
            else:
                diff = min(happy_change + 5, 0)
            diff = -round_stochastic(diff / 4)
            self.change_stress(diff)
            self.change_performance(
                randint(-4, 4) + round_stochastic((50 - self.stress) / 20)
            )
            if self.performance < 15 and randint(1, self.performance + 1) == 1:
                display_event(
                    _("You have been fired from your job.\nReason: Performance")
                )
                self.lose_job()
                self.change_happiness(-randint(20, 35))
            if self.stress > 65:
                amount = randint(0, round_stochastic((self.stress - 65) / 5))
                self.change_happiness(-amount)
                critical_stress = self.stress > 85
                if critical_stress:
                    self.change_health(round_stochastic((self.stress - 80) / 4))
                if amount > 0 and randint(1, 5 - critical_stress) == 1:
                    if critical_stress:
                        print(
                            _(
                                "You feel like you're on the verge of burnout from so much work!"
                            )
                        )
                    else:
                        print(_("You're feeling stressed out from all of this work."))
                if (
                    critical_stress
                    and "High Blood Pressure" not in self.illnesses
                    and randint(1, 7) == 1
                ):
                    display_event(_("You are suffering from high blood pressure."))
                    self.change_health(-randint(4, 8))
                    self.add_illness("High Blood Pressure")

    def get_job(self, salary):
        if not self.has_job:
            self.has_job = True
            self.salary = salary
            self.years_worked = 0
            self.stress = 45
            self.performance = 50
            self.job_hours = 40
            self.last_raise = self.age
            self.times_asked_since_last_raise = 0
            self.salary_years = []

    def lose_job(self):
        if self.has_job:
            self.has_job = False
            self.salary = 0
            self.years_worked = 0
            self.stress = 0
            self.performance = 0
            self.job_hours = 0
            self.salary_years = []

    def change_stress(self, amount):
        if self.has_job:
            self.stress = clamp(self.stress + amount, 0, 100)

    def change_performance(self, amount):
        if self.has_job:
            self.performance = clamp(self.performance + amount, 0, 100)

    def calc_grades(self, offset):
        self.grades = clamp(round(10 * math.sqrt(self.smarts + offset)), 0, 100)

    def get_gender_str(self):
        return _("Male") if self.gender == Gender.Male else _("Female")

    def die(self, message):
        print(message)
        if self.age == 0:
            score = self.happiness
        else:
            avg_happy = round(self.total_happiness / self.age)
            score = self.happiness * 0.3 + avg_happy * 0.7
        print_align_bars((_("Lifetime Happiness"), avg_happy), (_("Karma"), self.karma))
        self.delete_save()
        press_enter()
        raise PlayerDied

    def display_stats(self):
        if self.happiness >= 60:
            if self.happiness >= 85:
                symbol = ":D"
            else:
                symbol = ":)"
        elif self.happiness < 40:
            if self.happiness < 15:
                symbol = ":'("
            else:
                symbol = ":("
        else:
            symbol = ":|"

        if self.looks < 15:
            looks_symbol = "🌧"
        elif self.looks < 30:
            looks_symbol = "☁"
        elif self.looks < 43:
            looks_symbol = "🌥"
        elif self.looks < 55:
            looks_symbol = "⛅"
        elif self.looks < 65:
            looks_symbol = "🌤"
        elif self.looks < 85:
            looks_symbol = "☉"
        else:
            looks_symbol = "🔥"
        print_align_bars(
            (_("Happiness"), self.happiness, symbol),
            (_("Health"), self.health, "</3" if self.health < 20 else "<3"),
            (_("Smarts"), self.smarts),
            (_("Looks"), self.looks, looks_symbol),
            show_percent=True,
        )

    def can_retire(self):
        return self.years_worked >= 10 and player.age >= 65

    @property
    def marital_status(self):
        if not self.partner:
            return 0
        return self.partner.status + 1

    def lose_partner(self):
        if self.partner in self.relations:
            self.relations.remove(self.partner)
        self.partner = None

    def divorce(self):
        amount = round(self.money * random.uniform(0.4, 0.6))
        if amount > 0:
            self.change_happiness(-randint(10, 15))
            display_event(
                _(
                    "The judge has ordered you to pay {name} ${amount} to settle your divorce."
                ).format(name=self.partner.name, amount=amount)
            )
            self.money -= amount
        self.lose_partner()

    def update_hours(self, hours):
        prev = self.job_hours
        self.job_hours = hours
        self.change_stress(round((self.job_hours - prev) * 0.75))

    def random_events(self):
        if self.age >= 5 and randint(1, 5000) == 1:
            print(_("You were struck by lightning!"))
            good_or_bad = (
                randint(1, 2) == 1
            )  # TODO: Should I make the chance for it to be good or bad based on your karma?
            if good_or_bad:
                self.change_happiness(100)
                self.change_health(100)
                self.change_smarts(100)
                self.change_looks(100)
            else:
                self.change_happiness(-100)
                self.change_health(-100)
                self.change_smarts(-100)
                self.change_looks(-100)
            self.display_stats()
            press_enter()
            if not good_or_bad and randint(1, 5) == 1:
                self.die(_("You died after being struck by lightning."))
        if self.has_job:
            self.years_worked += 1
        if self.salary > 0:
            money = self.salary * self.job_hours / 40
            tax = calculate_tax(self.salary)
            income = self.salary - tax
            income *= random.uniform(0.4, 0.8)  # Expenses
            self.money += round_stochastic(income)
        if self.uv_years > 0:
            self.uv_years -= 1
            if self.uv_years == 0:
                self.grades = None
                display_event(_("You graduated from university."))
                self.change_happiness(randint(14, 20))
                self.change_smarts(randint(10, 15))
                if self.chose_student_loan:
                    self.student_loan = randint(20000, 40000)
                    print(_("You now have to start paying back your student loan"))
            else:
                if self.grades < randint(10, 45):
                    display_event(
                        _("You were expelled from university after earning bad grades.")
                    )
                    self.change_happiness(-randint(30, 50))
        if self.student_loan > 0:
            amount = min(randint(1000, 3000) for _ in range(3))
            amount = min(amount, self.student_loan)
            self.money -= amount
            self.student_loan -= amount
            if self.student_loan == 0:
                print(_("You've fully paid off your student loan"))
        for illness in self.illnesses[:]:
            if illness == "Depression":
                if self.happiness >= randint(20, 35):
                    display_event(_("You are no longer suffering from depression"))
                    self.change_happiness((100 - self.happiness) // 2)
                    self.change_health(randint(4, 8))
                    self.remove_illness("Depression")
                else:
                    self.change_happiness(-randint(1, 2))
                    self.change_health(-randint(1, 4))
            elif illness == "High Blood Pressure":
                self.change_health(-randint(1, 5))
                if self.stress > randint(80, 95) and self.health < randint(1, 10):
                    if randint(1, 3) == 1:
                        self.die(_("You died due to a massive heart attack."))
                elif self.stress < randint(25, 60) and randint(1, 2) == 1:
                    display_event(
                        _("You are no longer suffering from high blood pressure")
                    )
                    self.change_happiness(randint(4, 8))
                    self.change_health(randint(4, 8))
                    self.remove_illness("High Blood Pressure")
        if self.age == 2 and randint(1, 2) == 1:
            print(
                _("Your mother is taking to to the doctor's office to get vaccinated.")
            )
            print(_("How will you behave?"))
            choices = [_("Try to stay calm"), _("Throw a tantrum"), _("Bite her")]
            choice = choice_input(*choices)
            clear_screen()
            if choice == 1:
                print(_("You remained calm"))
            elif choice == 2:
                self.change_happiness(-randint(25, 35))
                self.parents["Mother"].change_relationship(-randint(6, 10))
                print(_("You threw a tantrum"))
            elif choice == 3:
                self.change_happiness(-randint(6, 10))
                self.parents["Mother"].change_relationship(-randint(25, 35))
                print(_("You bit your mother"))
        if self.is_in_school():
            self.change_grades(randint(-3, 3))
            base = round(10 * math.sqrt(self.smarts))
            if self.grades < base - 2:
                self.change_grades(randint(1, 3))
            elif self.grades > base + 2:
                self.change_grades(-randint(1, 3))
            grade_delta = (self.happiness - 50) / 10
            if grade_delta > 0:
                grade_delta /= 2
            self.change_grades(round_stochastic(grade_delta))
        if self.has_trait("GENIUS"):
            if self.age < randint(18, 25):
                self.change_smarts(randint(0, 9))
            else:
                self.change_smarts(randint(0, 4))
        if self.age == 6:
            print(_("You are starting elementary school"))
            self.change_smarts(randint(1, 2) + 2 * self.has_trait("GENIUS"))
            self.calc_grades(randint(4, 8))
        if self.age == 12:
            print(_("You are starting middle school"))
            self.change_smarts(randint(1, 3) + 3 * self.has_trait("GENIUS"))
            self.calc_grades(randint(0, 8))
        if self.age == 14:
            print(_("You are starting high school"))
            self.change_smarts(randint(1, 4) + 4 * self.has_trait("GENIUS"))
            self.calc_grades(randint(-8, 8))
        if 1 <= self.marital_status <= 2:
            if self.partner.relationship < randint(25, 35) and randint(1, 3) == 1:
                name = self.partner.name_accusative()
                print(
                    _("Your {partner} wants to break up with you.").format(partner=name)
                )
                print(_("What will you do?"))
                him_her = self.partner.him_her()
                choices = choice_input(
                    _("Wish {him_her} well").format(him_her=him_her),
                    _("Beg {him_her} to stay").format(him_her=him_her),
                )
                self.change_happiness(-randint(15, 18))
                if choice == 1:
                    print(
                        _("You wished {name} the best").format(name=self.partner.name)
                    )
                    self.lose_partner()
                elif choice == 2:
                    print(
                        _("You begged {name} to stay with you.").format(
                            name=self.partner.name
                        )
                    )
                    he_she = self.partner.he_she().capitalize()
                    if randint(1, 100) > partner.willpower:
                        display_event(
                            _("{he_she} decided to stay with you.").format(
                                he_she=he_she
                            )
                        )
                    else:
                        display_event(
                            _("{he_she} dumped you anyway.").format(he_she=he_she)
                        )
                        self.lose_partner()
                        self.change_happiness(-randint(10, 20))
        elif self.marital_status == 3:
            if self.partner.relationship <= randint(15, 30) and randint(1, 7) == 1:
                name = self.partner.name_accusative()
                print(_("Your {partner} wants a divorce.").format(partner=name))
                print(_("What will you do?"))
                him_her = self.partner.him_her()
                choices = choice_input(
                    _("Wish {him_her} well").format(him_her=him_her),
                    _("Beg {him_her} to stay").format(him_her=him_her),
                )
                self.change_happiness(-randint(15, 18))
                if choice == 1:
                    print(
                        _("You honored {name}'s request for a divorce.").format(
                            name=self.parter.name
                        )
                    )
                    self.divorce()
                elif choice == 2:
                    print(
                        _("You begged {name} to stay with you.").format(
                            name=self.partner.name
                        )
                    )
                    he_she = self.partner.he_she().capitalize()
                    if min(randint(1, 100) for _ in range(2)) > partner.willpower:
                        print(
                            _("{he_she} decided to stay with you.").format(
                                he_she=he_she
                            )
                        )
                    else:
                        display_event(
                            _("{he_she} insisted on getting a divorce.").format(
                                he_she=he_she
                            )
                        )
                        self.change_happiness(-randint(15, 22))
                        self.divorce()
        if (
            self.age >= 18
            and self.age < randint(42, 70)
            and self.marital_status == 0
            and randint(1, 16) == 1
        ):
            partner = self.generate_partner()
            if partner.compatibility_check(self):
                string = _("A male") if partner.gender == Gender.Male else _("A female")
                print(
                    _("{a_male_female} named {name} has asked you out.").format(
                        a_male_female=string, name=partner.name
                    )
                )
                partner.print_info()
                him_her = partner.him_her()
                option1 = _("Start dating {him_her}").format(him_her=him_her)
                option2 = _("Reject {him_her}").format(him_her=him_her)
                choice = choice_input(option1, option2)
                if choice == 1:
                    self.change_happiness(randint(12, 20))
                    print(_("You are now dating {name}.").format(name=partner.name))
                    self.partner = partner
                    self.relations.append(partner)
        if self.age == 17 and not self.dropped_out:
            self.grades = None
            print(_("You graduated from high school."))
            self.change_happiness(randint(15, 20))
            self.change_smarts(randint(6, 10))
            print()
            self.display_stats()
            print()
            print(_("Would you like to apply to university?"))
            choice = choice_input(_("Yes"), _("No"))
            clear_screen()
            if choice == 1:
                if self.smarts >= random.randint(28, 44):
                    print(_("Your application to university was accepted!"))
                    self.change_happiness(randint(7, 9))
                    SCHOLARSHIP = _("Scholarship")
                    LOAN = _("Student Loan")
                    PARENTS = _("Ask parents to pay")
                    choices = [SCHOLARSHIP, LOAN, PARENTS]
                    chosen = False
                    while not chosen:
                        print(_("How would you like to pay for your college tuition?"))
                        choice = choice_input(*choices, return_text=True)
                        clear_screen()
                        if choice == SCHOLARSHIP:
                            if self.smarts >= randint(randint(75, 85), 100):
                                display_event(
                                    _("Your scholarship application has been awarded!")
                                )
                                self.change_happiness(
                                    randint(10, 15) + (10 * self.has_trait("CHEERFUL"))
                                )
                                chosen = True
                            else:
                                display_event(
                                    _("Your scholarship application was rejected.")
                                )
                                self.change_happiness(-randint(7, 9))
                                choices.remove(SCHOLARSHIP)
                        elif choice == PARENTS:
                            total = sum(p.generosity for p in self.parents.values())
                            avg = total / len(self.parents)
                            chance = (avg / 100) ** 4
                            if random.random() < chance:
                                display_event(
                                    _(
                                        "Your parents agreed to pay for your university tuition!"
                                    )
                                )
                                self.change_happiness(
                                    randint(7, 9) + (7 * self.has_trait("CHEERFUL"))
                                )
                                chosen = True
                            else:
                                display_event(
                                    _(
                                        "Your parents refused to pay for your university tuition."
                                    )
                                )
                                self.change_happiness(-randint(7, 9))
                                choices.remove(PARENTS)
                        else:
                            display_event(
                                _(
                                    "You took out a student loan to pay for your university tuition."
                                )
                            )
                            chosen = True
                            self.chose_student_loan = True
                    print(_("You are now enrolled in university."))
                    self.uv_years = 4
                    self.calc_grades(randint(-8, 10))
                else:
                    display_event(_("Your application to university was rejected."))
                    self.change_happiness(-randint(7, 9))
