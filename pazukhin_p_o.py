import math
import random

from astrobox.core import Drone
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class PazukhinDrone(Drone):
    steps_full = 0
    steps_half_full = 0
    steps_empty = 0
    stat_printed = False
    space_obj = None
    enemy = None
    enemies = None
    defence_positions = []
    attack_positions = []
    objects_with_elerium = []
    shot_distance = 635
    center_scene = None
    my_id = 0
    my_step = 0
    my_steps_in_defense = 0
    my_waiting_steps = 0
    my_last_coord = None
    all_elerium = 0

    def on_heartbeat(self):
        self.my_step += 1
        if self.near(self.defense_point()):
            self.my_steps_in_defense += 1
        if self.coord == self.my_last_coord and not self.near(self.defense_point()):
            self.my_waiting_steps += 1
        self.my_last_coord = self.coord

    def on_born(self):
        self.get_all_elerium()
        self.center_scene = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)
        self.get_defense_positions()
        available, asteroid = self.check_nearest_object_with_etherium()
        self.add_stat_and_move_to_obj(asteroid)

    def on_stop_at_asteroid(self, asteroid):
        if asteroid.payload == 0:
            self.choose_the_action()
        else:
            self.load_from(asteroid)
            self.turn_to(self.my_mothership)

    def on_load_complete(self):
        if self.payload != 100:
            self.choose_the_action()
        else:
            self.add_stat_and_move_to_obj(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        if mothership == self.my_mothership:
            if self.payload != 0:
                available, asteroid = self.check_nearest_object_with_etherium()
                if available:
                    self.turn_to(asteroid)
                self.unload_to(mothership)
            self.print_statistic(self.check_all_drones_on_mothership())
        else:
            self.turn_to(self.my_mothership)
            self.load_from(mothership)

    def on_unload_complete(self):
        self.choose_the_action()

    def on_wake_up(self):
        self.update_info()
        if self.check_health():
            self.add_stat_and_move_to_obj(self.my_mothership)
        elif self.payload != 0 and self.distance_to(self.my_mothership) <= 250:
            self.add_stat_and_move_to_obj(self.my_mothership)
        elif self.space_obj is not None and self.space_obj.payload != 0:
            self.turn_to(self.my_mothership)
            self.load_from(self.space_obj)
            self.space_obj = None
        else:
            self.choose_the_action()

    # ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

    def check_health(self):
        """Проверяем здоровье всех НАШИХ дронов

        :return: boolean
        """
        for tm in self.teammates:
            if tm.health <= 70 or self.health <= 70:
                return True
        return False

    def shift_point(self, enemy):
        """Получаем точку по направлению к противнику

        :param: ememy
        :return: point
        """
        vec = Vector.from_points(self.coord, enemy.coord, 15)
        point = Point(x=self.coord.x + vec.x, y=self.coord.y + vec.y)
        return point

    def get_enemies(self):
        """Обновляем список вражеских баз и дронов и сохраняем в self.enemies
        """
        motherships = []
        for mothership in self.scene.motherships:
            if mothership.is_alive and mothership != self.my_mothership:
                motherships.append(mothership)
        drones = []
        for drone in self.scene.drones:
            if drone.is_alive and drone.team != self.team:
                drones.append(drone)
        self.enemies = {'motherships': motherships, 'drones': drones}

    def get_object_with_etherium(self):
        """Обновляем список объектов с ресурсом и сохраняем в self.objects
        """
        self.objects_with_elerium = []
        temp_objects = []
        for mothership in self.scene.motherships:
            if not mothership.is_alive and mothership != self.my_mothership and mothership.payload != 0:
                temp_objects.append({'object': mothership, 'distance': self.my_mothership.distance_to(mothership)})
        for drone in self.scene.drones:
            if not drone.is_alive and drone.team != self.team and drone.payload != 0:
                temp_objects.append({'object': drone, 'distance': self.my_mothership.distance_to(drone)})
        for asteroid in self.asteroids:
            if asteroid.payload != 0:
                temp_objects.append({'object': asteroid, 'distance': self.my_mothership.distance_to(asteroid)})
        temp_objects = sorted(temp_objects, key=lambda x: x['distance'])
        objects = []
        for obj in temp_objects:
            if not self.check_object_on_fire(obj['object']):
                objects.append(obj['object'])
        self.objects_with_elerium = objects

    def get_defense_positions(self):
        """Получаем координаты для защиты базы"""
        self.defence_positions.clear()
        distance = 160
        angle = 60
        temp_positions_on_base = []
        center_scene = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)
        distances = [15, 0, -20, 0, 15]
        for dis in distances:
            vec = Vector.from_points(self.my_mothership.coord, center_scene, distance + dis)
            vec.rotate(angle)
            point = Point(x=self.my_mothership.coord.x + vec.x, y=self.my_mothership.coord.y + vec.y)
            distance_to = self.center_scene.distance_to(point)
            temp_positions_on_base.append({'point': point, 'distance': distance_to})
            angle -= 30
        temp_positions_on_base = sorted(temp_positions_on_base, key=lambda x: x['distance'])
        for point in temp_positions_on_base:
            self.defence_positions.append(point['point'])

    def get_my_id(self):
        """Присваиваем порядковый номер нашим дронам

        :return: new_id
        """
        comrades = [{'drone': self, 'id': self.id}]
        for teammate in self.teammates:
            comrades.append({'drone': teammate, 'id': teammate.id})
        comrades = sorted(comrades, key=lambda x: x['id'])
        new_id = 0
        for comrade in comrades:
            if self == comrade['drone']:
                return new_id
            else:
                new_id += 1

    def update_info(self):
        """Обновляем информацию по противникам ресурсам и т.д."""
        self.get_enemies()
        self.get_object_with_etherium()
        self.get_defense_positions()
        self.my_id = self.get_my_id()

    def defense_point(self):
        """Возвращаем координаты точки обороны для определнного дрона

        :return: point
        """
        point = self.defence_positions[self.my_id]
        return point

    def check_enemy_on_protection(self, enemy):
        """Проверяем находится ли противник под защитой

        :return: boolean
        """
        if enemy in self.enemies['drones']:
            for mothership in self.enemies['motherships']:
                if enemy.my_mothership == mothership and 50 < enemy.distance_to(mothership) <= 300:
                    return True
            return False
        count = 0
        if enemy in self.enemies['motherships']:
            for drone in self.enemies['drones']:
                if drone.my_mothership == enemy and 50 < enemy.distance_to(drone) <= 350:
                    count += 1
            if count >= 1:
                return True
            return False

    def check_object_on_fire(self, obj):
        """Проверяем находится ли объект в зоне досягаемости вражеских орудий

        :return: boolean
        """
        for drone in self.enemies['drones']:
            if drone.distance_to(obj) <= self.shot_distance:
                return True
        return False

    def get_min_id(self):
        """Возвращаем миинмальный id среди наших дронов

        :return: min_id
        """
        min_id = self.id
        for tm in self.teammates:
            if tm.id < min_id:
                min_id = tm.id
        return min_id

    def check_nearest_object_with_etherium(self):
        """Возвращает ближайший непустой астероид
        доступени или нет(boolean), ближайший asteroid или None, если такового нет

        :return: available, asteroid
        """
        asteroid = None
        available = False
        asts = []
        distance = 0
        center_scene = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)
        for stone in self.asteroids:
            if stone.payload >= 90 and self.distance_to(stone) > distance \
                    and self.my_mothership.distance_to(stone) > 250:
                max_distance = self.my_mothership.distance_to(center_scene) * 0.75
        for stone in self.asteroids:
            if stone.payload >= 90 and self.my_mothership.distance_to(stone) > 250 and (
                    self.distance_to(stone) <= max_distance):
                asts.append({'stone': stone, 'payload': self.distance_to(stone)})
        asts = sorted(asts, key=lambda x: x['payload'])
        min_id = self.get_min_id()
        if len(asts) != 0:
            if len(asts) >= self.id - min_id:
                available = True
                asteroid = asts[self.id - min_id - 1]['stone']
            else:
                available = True
                asteroid = random.choice(asts)['stone']
        if (75 < self.payload < 100) or (asteroid is None and available is False):
            distance = 9999999.99999
            for stone in self.asteroids:
                if stone.payload != 0 and self.distance_to(stone) < distance:
                    distance = self.distance_to(stone)
                    available = True
                    asteroid = stone
        if (75 < self.payload < 100) or (asteroid is None and available is False):
            distance = 9999999.99999
            for drone in self.scene.drones:
                if drone.payload != 0 and self.distance_to(drone) < distance and not drone.is_alive:
                    distance = self.distance_to(drone)
                    available = True
                    asteroid = drone
        if (75 < self.payload < 100) or (asteroid is None and available is False):
            distance = 9999999.99999
            for mothership in self.scene.motherships:
                if mothership.payload != 0 and self.distance_to(mothership) < distance and not mothership.is_alive:
                    distance = self.distance_to(mothership)
                    available = True
                    asteroid = mothership
        return available, asteroid

    def search_nearest_enemy(self):
        """Возвращает ближайшего противника
        доступени или нет(boolean), ближайший противник или None, если такового нет

        :return: available, enemy
        """
        self.get_enemies()
        available = False
        enemy = None
        distance = 99999999.99999
        for drone in self.enemies['drones']:
            if self.my_mothership.distance_to(drone) < distance and not self.check_enemy_on_protection(drone):
                distance = self.my_mothership.distance_to(drone)
                available = True
                enemy = drone
        if not available:
            for mothership in self.enemies['motherships']:
                if not self.check_enemy_on_protection(mothership):
                    enemy = mothership
                    available = True
        return available, enemy

    def add_stat(self, obj):
        """Сохраняем дистанцию перемещения в статистику
        в зависимости от загруженности дрона
        """
        distance = self.distance_to(obj)
        if self.payload == 0:
            self.steps_empty += distance
        elif self.payload == 100:
            self.steps_full += distance
        elif 1 <= self.payload <= 99:
            self.steps_half_full += distance

    def add_stat_and_move_to_obj(self, space_object):
        """Сохраняем перемещение в статистику и перемещаемся"""
        self.stop()
        self.add_stat(space_object)
        self.move_at(space_object)

    def print_statistic(self, all_on_mothership):
        """Если все дроны на базе и нет непустых астероидов
        выводится статистика"""
        available = False
        for asteroid in self.asteroids:
            if asteroid.payload != 0:
                available = True
        stat_printed = False
        for drone in self.teammates:
            if drone.stat_printed:
                stat_printed = True
        if all_on_mothership and not stat_printed and not available:
            steps_full = 0
            steps_half_full = 0
            steps_empty = 0
            for drone in self.teammates:
                steps_full = drone.steps_full
                steps_half_full = drone.steps_half_full
                steps_empty = drone.steps_empty
                all_steps = steps_full + steps_half_full + steps_empty
            print(f'Пройдено полным {round((steps_full * 100) / all_steps)} процентов от пройденного пути')
            print(f'Пройдено полупустым {round((steps_half_full * 100) / all_steps)} процентов от пройденного пути')
            print(f'Пройдено пустым {round((steps_empty * 100) / all_steps)} процентов от пройденного пути')
            self.stat_printed = True

    def check_all_drones_on_mothership(self):
        """Проверяем все ли дроны на базе

        :return: Boolean
        """
        all_on_mothership = True
        available, asteroid = self.check_nearest_object_with_etherium()
        enemy_av, enemy = self.search_nearest_enemy()
        for drone in self.teammates:
            if not drone.near(self.my_mothership):
                all_on_mothership = False
        if available or enemy_av:
            all_on_mothership = False
        return all_on_mothership

    def get_angle(self, position, teammate, enemy):
        """Получает угол между векторами position-enemy и teammate-enemy
        """

        def scalar(vec1, vec2):
            return vec1.x * vec2.x + vec1.y * vec2.y

        v12 = Vector(position.x - enemy.x, position.y - enemy.y)
        v32 = Vector(teammate.x - enemy.x, teammate.y - enemy.y)
        _cos = scalar(v12, v32) / (v12.module * v32.module + 1.e-8)
        return math.degrees(math.acos(_cos))

    def check_firing_line(self, enemy, position):
        """Проверяем нет ли рядом или на линии огня наших teammates, чтобы их не подстрелить

        :return: boolean
        """
        flag = True
        for teammate in self.teammates:
            xy0 = teammate.coord
            xy1 = position
            xy2 = enemy.coord
            chisl = abs((xy2.y - xy1.y) * xy0.x - (xy2.x - xy1.x) * xy0.y + xy2.x * xy1.y - xy2.y * xy1.x)
            znam = math.sqrt((xy2.y - xy1.y) ** 2 + (xy2.x - xy1.x) ** 2)
            dist = chisl / znam
            if dist < 20 or (self.get_angle(position, teammate.coord, enemy.coord) < 30
                             and teammate.distance_to(position) < 45) \
                    or teammate.distance_to(position) < 25 or teammate.distance_to(enemy) < 20:
                flag = False
                break
        return flag

    def check_win(self):
        """Проверяем, что у нас больше всех ресурсов

        :return: boolean
        """
        for mothership in self.enemies['motherships']:
            if mothership.payload >= self.my_mothership.payload:
                return False
        return True

    def get_all_elerium(self):
        for ast in self.asteroids:
            self.all_elerium += ast.payload

    def clear_my_steps_in_defense(self):
        """Обнуляем количество шагов нахождения в защите
        """
        self.my_steps_in_defense = 0
        for tm in self.teammates:
            tm.my_steps_in_defense = 0

    def attack_point(self):
        """Получаем координаты точки нападения"""
        if len(self.attack_positions) > self.my_id:
            point = self.attack_positions[self.my_id]
        else:
            point = self.defence_positions[self.my_id]
        return point

    def get_attack_positions(self, enemy):
        """Формируем список координат точек нападения"""
        temp_attack_positions = []
        distance = self.shot_distance + 20
        angle = 24
        distances = [20, 15, 10, 5, 0, 5, 10, 15, 20]
        test_points = []
        for dis in distances:
            vec = Vector.from_points(enemy.coord, self.my_mothership.coord, distance + dis)
            vec.rotate(angle)
            point = Point(x=enemy.coord.x + vec.x, y=enemy.coord.y + vec.y)
            test_points.append(point)
            if int(point.x) in range(50, 1150) and int(point.y) in range(50, 1150) \
                    and not self.my_mothership.distance_to(point) < 100:
                temp_attack_positions.append({'point': point,
                                              'distance': self.my_mothership.distance_to(point)})
            angle -= 6
        temp_attack_positions = sorted(temp_attack_positions, key=lambda x: x['distance'])
        self.attack_positions.clear()
        for a_p in temp_attack_positions:
            self.attack_positions.append(a_p['point'])

    def choose_the_action(self):
        """Выбираем действие,
        зависит от того есть ли непустые астероиды
        после того как закончились астероиды вступаем в бой с противником
        по возможности собираем etherium с обломков или сидим в обороне
        """
        # PREPARATION
        self.get_enemies()
        self.get_object_with_etherium()
        self.my_id = self.get_my_id()
        available, asteroid = self.check_nearest_object_with_etherium()
        # Если враг обозначен
        if self.enemy is not None:
            # Враг уничтожен или покинул зону досягаемости орудий
            if not self.enemy.is_alive or self.distance_to(self.enemy) > self.shot_distance + 20:
                self.enemy = None
                enemy_av = False
            # Враг повторно переназначается
            else:
                enemy = self.enemy
                enemy_av = True
        # Если враг не обозначен
        if self.enemy is None:
            # Поиск ближайшего врага
            enemy_av, enemy = self.search_nearest_enemy()
            if not enemy_av and len(self.enemies['drones']) < len(self.teammates) + 2 \
                    and len(self.enemies['drones']) != 0:
                enemy_av = True
                enemy = self.enemies['drones'][0]
        # Если враг есть -> атакуем
        if enemy_av:
            self.get_attack_positions(enemy)
            self.enemy = enemy
        # Если завис надолго отправляем на бвзу (не помогает)
        if self.my_waiting_steps > 500 and not self.check_win():
            self.add_stat_and_move_to_obj(self.defense_point())

        # Выбор дейстия
        # Не добрали ресурса до необходимого минимума и есть доступный источник -> летим к источнику
        if available and self.my_mothership.payload < self.all_elerium // 4:
            self.add_stat_and_move_to_obj(asteroid)
        # Условия, при которых переходим в оборону
        elif not self.near(self.defense_point()) \
                and ((self.check_win() and not available)
                     or (enemy_av and self.my_mothership.distance_to(enemy) <= self.shot_distance + 20)
                     or (len(self.enemies['drones']) > 5 and len(self.teammates) < 3)):
            self.clear_my_steps_in_defense()
            self.add_stat_and_move_to_obj(self.defense_point())
        # Враг в зоне досягаемости -> поворачиваемся и стреляем
        elif enemy_av and self.distance_to(enemy) <= self.shot_distance + 100 \
                and (self.check_firing_line(enemy, self.coord) or self.near(self.defense_point())):
            self.turn_to(enemy)
            if self.distance_to(enemy) <= self.shot_distance + 50:
                self.gun.shot(enemy)
            if self.my_waiting_steps > 25:
                self.my_waiting_steps = 0
                self.add_stat_and_move_to_obj(self.shift_point(enemy))
        # Условия для перехода в наступление
        elif enemy_av and (self.my_steps_in_defense > 200 or len(self.enemies['drones']) < 5) \
                and not self.check_enemy_on_protection(enemy) \
                and (self.my_mothership.distance_to(enemy) >= self.shot_distance + 20 or not self.check_win()):
            self.my_steps_in_defense = 0
            self.add_stat_and_move_to_obj(self.attack_point())
        # Условия, при которых подбираем ресурс с объектов
        elif len(self.objects_with_elerium) != 0 and (self.my_id == 0 or len(self.enemies['drones']) < 5):
            for obj in self.objects_with_elerium:
                if (self.check_enemy_on_protection(enemy)
                    or self.my_mothership.distance_to(obj) <= 450) \
                        and not self.check_object_on_fire(obj):
                    self.space_obj = obj
                    self.add_stat_and_move_to_obj(self.space_obj)
                    break
        # В остальных случаях сидим в обороне
        elif not self.near(self.defense_point()):
            self.add_stat_and_move_to_obj(self.defense_point())


drone_class = PazukhinDrone
