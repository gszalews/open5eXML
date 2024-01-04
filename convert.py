import json
import re
import requests

def main():
    print("1) Menagerie\n2) Tome of Beasts\n3) Tome of Beasts 2\n4) Tome of Beasts 3\n5) Creature Codex")
    choices = ["", "menagerie", "tob", "tob2", "tob3", "cc"]
    n = int(input("Choice: "))
    if n > 0 and n < len(choices):
        monsters = get_monsters(choices[n])
    else:
        exit
    final_list = ['<?xml version="1.0" encoding="UTF-8"?>','<compendium version="5" auto_indent="YES">', ""]
    for monster in monsters:
        final_list.append(convert_monster(monster, choices[n]))
        final_list.append("\n")
    final_list.append("</compendium>")
    final_string = "\n".join(final_list)
    with open(f"{choices[n]}.xml", "w", encoding="utf-8") as output:
        output.write(final_string)
        

def get_monsters(tag):
    '''
    Get enemies from open5e API

    :param slug: Document slug for use in API call
    :type slug: str
    :return: A list of enemies in JSON format
    :rtype: list

    '''
    url = f"https://api.open5e.com/monsters/?document__slug={tag}"
    total_results = []
    response = requests.get(url)
    data = response.json()
    total_results = total_results + data["results"]

    # Loop to handle multi-page return from API call
    while data["next"] is not None:
        response = requests.get(data["next"])
        data = response.json()
        total_results = total_results + data["results"]
    return total_results


def convert_monster(monster: dict, tag: str):
    if tag == "menagerie":
        source = "a5e"
    else:
        source = tag
    final_strings = ["<monster>"]
    att1 = {"name": f"{monster['name']} - {source}",
            "size": monster["size"],
            "type": monster["type"] + " " + monster["subtype"],
            "alignment": monster["alignment"],
            "ac": f"{monster['armor_class']} ({monster['armor_desc']})",
            "hp": f"{monster['hit_points']} ({monster['hit_dice']})"}
    for key in att1.keys():
        try:
            final_strings.append(make_line(key, att1[key]))
        except KeyError:
            pass
    final_strings.append(make_line("speed", get_speed(monster["speed"])))
    att2 = {"init": monster["dexterity"] // 2 - 5,
            "str": monster["strength"],
            "dex": monster["dexterity"],
            "con": monster["constitution"],
            "int": monster["intelligence"],
            "wis": monster["wisdom"],
            "cha": monster["charisma"]}
    for key in att2.keys():
        try:
            final_strings.append(make_line(key, att2[key]))
        except KeyError:
            pass
    saves = {"Str": monster["strength_save"], "Dex": monster["dexterity_save"], "Con": monster["constitution_save"], "Int": monster["intelligence_save"], "Wis": monster["wisdom_save"], "Cha": monster["charisma_save"]}
    save_str = join_subdata("saves", saves)
    if save_str:
        final_strings.append(make_line("save", save_str))
    skills_str = join_subdata("skills", monster["skills"])
    if skills_str:
        final_strings.append(make_line("skill", skills_str))
    att3 = {"vulnerable": monster["damage_vulnerabilities"],
            "resist": monster["damage_resistances"],
            "immune": monster["damage_immunities"],
            "conditionImmune": monster["condition_immunities"],
            "senses": monster["senses"],
            "languages": monster["languages"],
            "cr": monster["challenge_rating"]}
    for key in att3.keys():
        try:
            final_strings.append(make_line(key, att3[key]))
        except KeyError:
            pass
    if monster["special_abilities"]:
        final_strings.append(process_tarl("trait", monster["special_abilities"]))
    if monster["actions"]:
        final_strings.append(process_tarl("action", monster["actions"]))
    if monster["reactions"]:
        final_strings.append(process_tarl("reaction", monster["reactions"]))
    if monster["legendary_actions"]:
        final_strings.append(process_tarl("legendary", monster["legendary_actions"]))
    if monster["environments"]:
        env_str = ", ".join(monster["environments"])
        final_strings.append("environment", env_str)
    if monster["desc"]:
        if len(monster["desc"]) > 0:
            monster["desc"] = monster["desc"].replace("\n", " ")
            final_strings.append(make_line("description", monster["desc"]))
    final_strings.append("</monster>")
    return "\n".join(final_strings)
    


def make_line(element: str, data):
    return f"  <{element}>{data}</{element}>"

def get_speed(speed_dict: dict):
    speed_str = []
    keys = list(speed_dict.keys())
    if "walk" in keys:
        speed_str.append(f"{speed_dict['walk']} ft.")
        speed_dict.pop("walk")
        keys.remove("walk")
    for key in keys:
        speed_str.append(f"{key.capitalize()}: {speed_dict[key]} ft.")
    if len(speed_str) > 1:
        return ", ".join(speed_str)
    elif len(speed_str) == 1:
        return speed_str[0]
    else:
        return "None"
    
def join_subdata(data_type: str, data: dict):
    s = []
    for key in data.keys():
        if data[key] != None:
            if data_type == "skill":
                s.append(f"[{key}] {data[key]}")
            else:
                s.append(f"{key} {data[key]}")
    if len(s) > 1:
        return ", ".join(s)
    if len(s) == 1:
        return s[0]
    else:
        return None
    

def process_tarl(data_type:str, data:list):
    whole_list = []
    for dict in data:
        keys = list(dict.keys())
        sub_lines = [f"  <{data_type}>"]
        if "name" in keys:
            sub_lines.append(make_line("name", dict["name"]))
        if "desc" in keys:
            sub_lines.append(make_line("text", dict["desc"]))
        if data_type == "action":
            att = get_hit(dict["desc"])
            if att == None:
                att = ""
            damage = get_damage(dict["desc"])
            d_list = []
            s = ""
            if damage:
                for d in damage:
                    d_list.append(make_line("attack", f"|{att}|{d['dice']}"))
            if len(d_list) > 1:
                s = "\n  ".join(d_list)
            if len(d_list) == 1:
                s = d_list[0]
            if len(s) > 0:
                sub_lines.append(s)
        sub_lines.append(f"</{data_type}>")
        whole_string = "\n  ".join(sub_lines)
        whole_list.append(whole_string)
    return "\n".join(whole_list)



def get_hit(desc:str):
    # Extract "to hit" value from desc
    if not desc or desc == None:
        return None
    hit_results = re.search(r"^.*\+(\d+) to hit.*$", desc)
    if hit_results:
        return (int(hit_results.group(1)))
    else:
        return None


def get_damage(desc:str):
    # Find damage done by action
    if not desc or desc == None:
        return None
    dmg = []
    dmg_results = re.findall(r" (\d+) \((.*?)\) (\b\w*) damage", desc)
    if dmg_results:
        for d in range(len(dmg_results)):
            dmg.append({"dmg": int(dmg_results[d][0]), "dice": dmg_results[d][1], "type": dmg_results[d][2]})
    else:
        dmg = None
    return dmg


if __name__ == "__main__":
    main()