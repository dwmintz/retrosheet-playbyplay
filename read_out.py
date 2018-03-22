#!/usr/bin/python

import sys
import csv
from collections import defaultdict
from collections import OrderedDict
import re


# Parse the arguments passed in at the command line


game_info = dict()
plays = defaultdict(list)
lineups = dict()
data = defaultdict(list)
positions = {
            "1": "P",
            "2": "C",
            "3": "1B",
            "4": "2B",
            "5": "3B",
            "6": "SS",
            "7": "LF",
            "8": "CF",
            "9": "RF",
            "10": "DH",
            "11": "PH",
            "12": "PR"}
r_bases = {
          "B": "Batter",
          "1": "Runner on 1st",
          "2": "Runner on 2nd",
          "3": "Runner on 3rd"
}
bases = {
        "H": "home",
        "1": "1st base",
        "2": "2nd base",
        "3": "3rd base"
}
play_number = 0
infos = set()
pitch_seq = dict()
stats = {}


class Other_Stats(object):
    player, stat = "", ""

    def __init__(self, play_number):
        self.play_number = play_number


class Batter_Stats(object):
    pa, ab, h, d, t, hr, rbi, bb, so, gdp, hbp, sh, sf, ibb = [0] * 14

    def __init__(self, play_id):
        self.play_id = play_id

    def __str__(self):
        return ", ".join([str(self.play_id),
                          str(self.pa),
                          str(self.ab),
                          str(self.h),
                          str(self.d),
                          str(self.t),
                          str(self.hr),
                          str(self.rbi),
                          str(self.bb),
                          str(self.so),
                          str(self.gdp),
                          str(self.hbp),
                          str(self.sh),
                          str(self.sf),
                          str(self.ibb)
                          ])


class Pitcher_Stats(object):
    h, r, er, hr, bb, ibb, so, hbp, bk, wp = [0] * 10

    def __init__(self, play_id):
        self.play_id = play_id


class Situation(OrderedDict):

    def __init__(self):
        super(Situation, self).__init__()
        self['B'] = ''
        self['1'] = ''
        self['2'] = ''
        self['3'] = ''
        self['outs'] = 0


def parse_gamefiles(file):
    file_open = open(file)
    filereader = csv.reader(file_open, delimiter=',', quotechar='"')
    game_id = ""
    

    for row in filereader:
        # ID rows indicate a new game
        # We initialize a new dict for the game's info
        # as well as new lineup dicts

        if row[0] == "id":
            game_id, play_number, inning, top_bottom, pitchers = process_id_row(row)
            sit = Situation()
            stats[game_id] = {"batting_stats": [], "pitching_stats": [],
                              "other_stats": []}

        # For each info row, we add it to the game's info dict
        # We also keep a set of all info field keys
        elif row[0] == "info":
            game_info[game_id][row[1]] = row[2]
            infos.add(row[1])
        # For rows listing the starting lineups we fill out the lineup dict
        # We set the first play for these lineups as 1
        elif row[0] == "start":
            process_lineups(row, pitchers, game_id)
        elif row[0] == "play":

            # These NP rows are placeholders for substitutions
            # We remove these rows entirely
            if row[6] == "NP":
                pass
            else:
                # New batter or new inning resets the count and baserunners
                if inning != row[1] or top_bottom != int(row[2]):
                    count = [0, 0]
                    sit = Situation()
                # New batter resets the count
                if sit["B"] != row[3]:
                    count = [0, 0]
                inning, top_bottom, sit["B"] = row[1], int(row[2]), row[3]
                c_pitcher = pitchers[top_bottom][0]
                # We break down the pitch sequence, the basic play
                # the play modifiers and the base advances
                # This will make for cleaner storage
                try:
                    # Still have to deal w/ multiple non-batter plays in a row
                    p_seq = re.split(r'\.', row[5])[-1]
                except IndexError:
                    p_seq = row[5]
                # Split each pitch (and include surrounding events)
                p_seq_split = re.sub(r'((?:[A-Z]\+[1-3]){1}|[A-Z]{1})', r'\1,',
                                     p_seq)[:-1]
                for p in p_seq_split:
                    # Skip separators and increment the pitch count
                    if p == ',':
                        pitchers[top_bottom][1] += 1
                    # If it's an actual pitch, start to build the row
                    else:
                        try:
                            # If it's still same pitch, add surrounding events
                            if pitch_seq[game_id][c_pitcher][-1][0] == pitchers[top_bottom][1]:
                                pitch_seq[game_id][c_pitcher][-1][4] += p
                            # Otherwise append the row
                            else:
                                p_row = [pitchers[top_bottom][1], inning,
                                         top_bottom, play_number, p, count[0],
                                         count[1]]
                                pitch_seq[game_id][c_pitcher].append(p_row)
                        # If it's a whole new pitch, append the row
                        except IndexError:
                            p_row = [pitchers[top_bottom][1], inning,
                                     top_bottom, play_number, p,
                                     count[0], count[1]]
                            pitch_seq[game_id][c_pitcher].append(p_row)
                    # Update the ball/strike count
                    if p in ("B", "I", "P", "V") and count[0] < 3:
                        count[0] += 1
                    elif p in ("C", "F", "K", "L", "M", "O", "Q", "R", "S", "T") and count[1] < 2:
                        count[1] += 1
                # Process the play

                start_sit = [v for k, v in sit.iteritems()]

                clean_play = row[6].replace('!', '').replace('?', '').replace('#', '')
                if game_id == 'ANA201008280' and play_number > 63:
                    import pdb; pdb.set_trace()  # breakpoint c322cb9b //

                end_sit, play_description, basic_play, advances, play_mods = process_play(clean_play, sit, game_id, play_number)

                # Once we've parsed everything we write a new play row
                plays[game_id].append([play_number, inning, top_bottom,
                                       start_sit[0], row[4], p_seq, basic_play,
                                       '/'.join(play_mods[1:]), advances,
                                       "; ".join(play_description)] + start_sit)
                # print [k for k,v in start_sit.iteritems()]
                # Then we increment the play_number, which is an
                # incrementer we've added
                play_number += 1
                pitchers[top_bottom][1] += 1
                sit = end_sit
        elif row[0] == "sub":
            # For substitution rows, we're only recording the details
            # of the sub himself. We'll assume the rest of the lineup
            # remains the same
            player = {"id": row[1], "position": positions[row[5]],
                      "order": row[4]}
            if row[3] == "0":
                # We use the play number to indicate when the substitution
                # took place
                lineups[game_id]["visitor"][str(play_number+1)] = list()
                lineups[game_id]["visitor"][str(play_number+1)].append(
                    player)
                if player["position"] == "P":
                    pitchers[1] = [player["id"], 1]
            elif row[3] == "1":
                lineups[game_id]["home"][str(play_number+1)] = list()
                lineups[game_id]["home"][str(play_number+1)].append(player)
                if player["position"] == "P":
                    pitchers[0] = [player["id"], 1]
        elif row[0] == "data":
            # Data rows are simple and just assign earned runs to pitchers
            data[game_id].append({row[2]: row[3]})


def process_id_row(row):
    game_id = row[1]
    game_info[game_id], lineups[game_id] = dict(), dict()
    lineups[game_id]["visitor"] = dict()
    lineups[game_id]["visitor"]["1"] = list()
    lineups[game_id]["home"] = dict()
    lineups[game_id]["home"]["1"] = list()
    pitch_seq[game_id] = defaultdict(list)
    play_number, inning, top_bottom, = 1, 1, 0
    pitchers = [["none", 1], ["none", 1]]

    return game_id, play_number, inning, top_bottom, pitchers


def process_lineups(row, pitchers, game_id):
    player = {"id": row[1], "position": positions[row[5]],
              "order": row[4]}
    if row[3] == "0":
        lineups[game_id]["visitor"]["1"].append(player)
        if player["position"] == "P":
            pitchers[1][0] = player["id"]
    elif row[3] == "1":
        lineups[game_id]["home"]["1"].append(player)
        if player["position"] == "P":
            pitchers[0][0] = player["id"]


def process_play(f_play, situation, game_id, play_number):
    b_s = Batter_Stats(play_number)
    play = re.split(r'\.', re.split(r'\/', f_play)[0])[0]
    try:
        play_mods = re.split(r'\/', re.split(r'\.', f_play)[0])
    except:
        play_mods = ""
    try:
        r_adv = re.split(r'\.', f_play)[1].rstrip()
    except IndexError:
        r_adv = "".rstrip()

    play_description = []
    sit = situation
    g_id = game_id
    pn = play_number

    # Split combo plays
    plays = play.split('+')
    i = 0

    for pl in plays:
        # For plays with multiple parts, make sure we only process the
        # runner advances once
        i += 1
        if i > 1:
            r_adv = ""

        # Define regex for batter plays
        if re.match(r'^[1-9]{1}$', pl):
            play_description.append("Fly ball caught by " + positions[pl])
            sit["outs"] += 1
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab = 1, 1
            if "SF" in play_mods:
                b_s.ab, b_s.sf = 0, 1
            elif "SH" in play_mods:
                b_s.ab, b_s.sh = 0, 1
        elif re.match(r'^[1-9]{2,}$', pl):
            play_description.append("Grounded out")
            sit["outs"] += 1
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab = 1, 1
            if "SF" in play_mods:
                b_s.ab, b_s.sf = 0, 1
            elif "SH" in play_mods:
                b_s.ab, b_s.sh = 0, 1
        elif re.match(r'(^[1-9]+\((B|[1-3])+\)$)', pl):
            play_description.append(r_bases[pl.split("(")[1][0]] + " put out")
            sit["outs"] += 1
            # Remove the baserunner who was thrown out
            sit[pl.split("(")[1][0]] = ""
            # This can be an implicit fielder's choice, so advance the batter
            b_d = "1" if pl.split("(")[1][0] != "B" else ""
            sit, n_narr = process_runners(r_adv, b_s, sit, b_d, g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab = 1, 1
            if "SF" in play_mods:
                b_s.ab, b_s.sf = 0, 1
            elif "SH" in play_mods:
                b_s.ab, b_s.sh = 0, 1
        elif re.match(r'(^(?:[1-9]+\((B|H|[1-3])\))[1-9]+$)', pl):
            play_description.append("Grounded into double play")
            sit["outs"] += 2
            # Remove the baserunner who was thrown out
            sit[pl.split("(")[1][0]] = ""
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.gdp = 1, 1, 1
        elif re.match(r'(^(?:[1-9]+\((B|H|[1-3])\)){2}$)', pl):
            play_description.append("Lined into double play")
            sit["outs"] += 2
            # Remove the baserunners who were out
            sit[pl.split("(")[1][0]] = ""
            sit[pl.split("(")[2][0]] = ""
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab = 1, 1
        elif re.match(r'(^(?:[1-9]+\((B|H|[1-3])\)){3}$)', pl):
            play_description.append("Triple play")
            sit["outs"] += 3
            b_s.pa, b_s.ab, b_s.gdp = 1, 1, 1
        elif re.match(r'^C\/E[1-3]$', pl):
            play_description.append("Interference on " + positions[pl[3]])
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn)
            play_description += n_narr
            b_s.pa = 1
        elif re.match(r'^S[1-9]*$', pl):
            play_description.append("Single")
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.h = 1, 1, 1
        elif re.match(r'^D[1-9]*$', pl):
            play_description.append("Double")
            sit, n_narr = process_runners(r_adv, b_s, sit, "2", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.h, b_s.d = 1, 1, 1, 1
        elif re.match(r'^T[1-9]*$', pl):
            play_description.append("Triple")
            sit, n_narr = process_runners(r_adv, b_s, sit, "3", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.h, b_s.t = 1, 1, 1, 1
        elif re.match(r'^DGR$', pl):
            play_description.append("Ground rule double")
            sit, n_narr = process_runners(r_adv, b_s, sit, "2", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.h, b_s.d = 1, 1, 1, 1
        elif re.match(r'^[1-9]*E[1-9]+$', pl):
            play_description.append("Batter reached on " + positions[pl.split("E")[1]] + " error")
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab = 1, 1
        elif re.match(r'^FC[1-9]+$', pl):
            play_description.append("Fielder's choice")
            b_s.pa, b_s.ab, b_s.h = 1, 1, 1
            if "X" in r_adv and "E" not in r_adv:
                sit["outs"] += 1
                b_s.h = 0
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn, True)
            play_description += n_narr
        elif re.match(r'^FLE[1-9]{1}$', pl):
            play_description.append(positions[pl[3]] + " error on foul fly ball")
        elif re.match(r'^(H|HR){1}$', pl):
            play_description.append("Home run")
            sit, n_narr = process_runners(r_adv, b_s, sit, "H", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.h, b_s.hr = 1, 1, 1, 1
        elif re.match(r'^(H|HR){1}[1-9]{1}$', pl):
            play_description.append("Inside-the-park home run")
            sit, n_narr = process_runners(r_adv, b_s, sit, "H", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.h, b_s.hr = 1, 1, 1, 1
        elif re.match(r'^HP$', pl):
            play_description.append("Batter hit by pitch")
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn)
            play_description += n_narr
            b_s.pa = 1
        elif re.match(r'^K$', pl):
            play_description.append("Struck out")
            sit["outs"] += 1
            b_s.pa, b_s.ab, b_s.so = 1, 1, 1
        elif re.match(r'^K[1-9]+$', pl):
            play_description.append("Struck out; Dropped third strike")
            sit["outs"] += 1
            b_s.pa, b_s.ab, b_s.so = 1, 1, 1
        elif re.match(r'^K[1-9]*\+(.*)$', pl):
            play_description.append("Struck out")
            sit["outs"] += 1
            b_s.pa, b_s.ab, b_s.so = 1, 1, 1
        elif re.match(r'^(I|IW)$', pl):
            play_description.append("Intentional walk")
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.ibb, b_s.bb = 1, 1, 1, 1
        elif re.match(r'^W$', pl):
            play_description.append("Walk")
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn)
            play_description += n_narr
            b_s.pa, b_s.ab, b_s.bb = 1, 1, 1
        elif re.match(r'^(?:IW|W|I)\+(.*)$', pl):
            play_description.append("Walk")
            sit, n_narr = process_runners(r_adv, b_s, sit, "1", g_id, pn)
            b_s.pa, b_s.ab, b_s.bb = 1, 1, 1
            if "I" in pl:
                b_s.pa, b_s.ab, b_s.bb = 1, 1, 1

        # Define regex for non-batter plays
        elif re.match(r'^BK$', pl):
            play_description.append("Balk")
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'^CS(2|3|H){1}\((?:[1-9]E[1-9])*|(?:[1-9])*\)$', pl):
            play_description.append("Runner caught stealing " + bases[pl[2]])
            if re.match(r'.*E.*', pl):
                "; ".join([play_description[-1], "safe because of error"])
            else:
                sit["outs"] += 1
                # Find the right runner to remove from base
                if pl[2] == "2":
                    sit["1"] = ""
                elif pl[2] == "3":
                    sit["2"] = ""
                elif pl[2] == "H":
                    sit["3"] = ""
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'^DI$', pl):
            play_description.append("Runner takes base without a throw")
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'^(PB|WP)$', pl):
            play_description.append("Wild pitch")
            # Take away the out if the batter's advance is given
            # explicitly
            if "B-" in r_adv:
                sit["outs"] -= 1
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'^SB(2|3|H){1}$', pl):
            play_description.append("Stolen base")
            dest = pl[2]
            if r_adv == "":
                if dest == "2":
                    r_adv = "1-2"
                elif dest == "3":
                    r_adv = "2-3"
                elif dest == "H":
                    r_adv = "3-H"
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'^SB(2|3|H){1};SB(2|3|H){1}$', pl):
            play_description.append("Double steal")
            steals = pl.split(";")
            r_advl = []
            for steal in steals:
                dest = steal[2]
                if steal[2] == "2":
                    r_advl.append("1-2")
                elif steal[2] == "3":
                    r_advl.append("2-3")
                elif steal[2] == "H":
                    r_advl.append("3-H")
            r_adv = ";".join(r_advl)
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'^SB(2|3|H){1};SB(2|3|H){1};SB(2|3|H){1}$', pl):
            play_description.append("Triple steal")
            steals = pl.split(";")
            r_advl = []
            for steal in steals:
                dest = pl[2]
                if steal[2] == "2":
                    r_advl.append("1-2")
                elif steal[2] == "3":
                    r_advl.append("2-3")
                elif steal[2] == "H":
                    r_advl.append("3-H")
            r_adv = ";".join(r_advl)
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'PO[1-3]{1}\([1-9]+\)$', pl):
            play_description.append("Picked off " + bases[pl[2]])
            sit["outs"] += 1
            sit[pl[2]] = ""
        elif re.match(r'PO[1-3]{1}\(E[1-9]+\)$', pl):
            play_description.append("Picked off " + bases[pl[2]])
            play_description.append("Error by " + positions[pl.split("E")[1][0]])
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr
        elif re.match(r'^POCS(2|3|H){1}\([1-9]+\)$', pl):
            play_description.append("Runner picked off stealing " + bases[pl[4]])
            sit["outs"] += 1
            # Find the right runner to remove from base
            if pl[4] == "2":
                sit["1"] = ""
            elif pl[4] == "3":
                sit["2"] = ""
            elif pl[4] == "H":
                sit["3"] = ""
            sit, n_narr = process_runners(r_adv, b_s, sit, "", g_id, pn)
            play_description += n_narr

    stats[game_id]["batting_stats"].append(b_s)
    return sit, play_description, play, r_adv, play_mods


def process_runners(r_adv, bat_stat, situation, batter_dest, game_id,
                    play_number, fc=False):
    if r_adv == "" and batter_dest == "":
        return situation, ''
    else:
        advances = r_adv.split(';')
        narr = []
        error = False

        try:
            for adv in advances:
                error = False
                # Advance non-batters first
                orig = adv[0]
                if orig != "B":
                    dest = adv[2]
                    success = True if adv[1] == '-' else False
                    if "E" in adv:
                        error = adv.split("E")[1][0]
                        # If runner would have been out but for error, negate
                        # the error
                        if success is False and fc is False:
                            situation["outs"] -= 1

                    situation, n_narr = advance_runner(orig, success, dest,
                                                       error, situation,
                                                       game_id, play_number,
                                                       bat_stat, adv)
                    narr.append(n_narr)
        except IndexError:
            pass

        # Batter advances can be implicitly indicated in the play
        # and/or explicitly indicated as runner advances, overruling
        # what's indicated in the play.

        # Advance batter if indicated by the play and no explicit
        # batter advance is given
        if batter_dest in ("1", "2", "3", "H") and "B" not in r_adv:
            orig = "B"
            dest = batter_dest
            success = True
            situation, n_narr = advance_runner(orig, success, dest, False,
                                               situation, game_id, play_number,
                                               bat_stat, adv)
        # Advance batter if indicated in runner advances
        # This gives us belt and suspenders
        try:
            for adv in advances:
                error = False
                orig = adv[0]
                if orig == "B":
                    dest = adv[2]
                    success = True if adv[1] == '-' else False
                    if "E" in adv:
                        error = adv.split("E")[1][0]
                        # If batter would have been out but for error, negate
                        # the error
                        if success is False:
                            situation["outs"] -= 1
                    situation, n_narr = advance_runner(orig, success, dest,
                                                       error, situation,
                                                       game_id, play_number,
                                                       bat_stat, adv)
                    narr.append(n_narr)
        except IndexError:
            pass

    return situation, narr


def advance_runner(runner, success, dest, error, situation, game_id,
                   play_number, bat_stat, adv):
    ar_narr = ''
    try:
        runner_name = situation[runner]
        if (success) or (not success and error):
            if runner == dest:
                ar_narr += r_bases[runner] + " stays at " + bases[dest]
            elif dest == "H":                
                # Add the run
                new_row = Other_Stats(play_number)
                new_row.stat = "run"
                new_row.player = runner_name
                # Test for bad runs
                assert runner_name != '', game_id + " - " + str(play_number) + adv
                stats[game_id]["other_stats"].append(new_row)
                # Add the RBI
                if "NR" not in adv and "NORBI" not in adv:
                    bat_stat.rbi += 1
                if error:
                    ar_narr = "After error by " + positions[error] + " "
                ar_narr += r_bases[runner] + " scores"
                situation[runner] = ''
            else:
                situation[dest] = runner_name
                situation[runner] = ''
                if error:
                    ar_narr = "After error by " + positions[error] + " "
                ar_narr += r_bases[runner] + " advances to " + bases[dest]
        elif not success and not error:
            situation[runner] = ''
            ar_narr = r_bases[runner] + " out at " + bases[dest]

    except IndexError:
        pass
    return situation, ar_narr


def write_out(game_info_dict, data_dict, lineup_dict, play_dict, stats):
    info_keys = sorted(infos)
    with open('game_info.csv', 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["game_id"] + info_keys)
        row = []
        for k, v in game_info.iteritems():
            row = [k]
            for key in info_keys:
                try:
                    row.append(v[key])
                except:
                    row.append("")
            writer.writerow(row)

    with open('lineups.csv', 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["game_id", "home_away", "first_play", "id",
                        "order_up", "position"])
        for k, v in lineup_dict.iteritems():
            game_id = k
            for t, p in v.iteritems():
                home_away = t
                for fp, ps in p.iteritems():
                    first_play = fp
                    for pops in ps:
                        player = pops["id"]
                        order_up = pops["order"]
                        pos = pops["position"]
                        writer.writerow([game_id, home_away, first_play,
                                         player, order_up, pos])

    with open('earned_runs.csv', 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["game_id", "player_id", "earned_runs"])
        for k, v in data_dict.iteritems():
            game_id = k
            for pitchers in v:
                for pl, er in pitchers.iteritems():
                    writer.writerow([game_id, pl, er])

    with open('playbyplay.csv', 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["game_id", "play_number", "inning", "top_bottom",
                         "batter", "count", "pitch_seq", "play_scoring",
                         "modifiers", "runner_advances", "description", "batter",
                         "1B_runner", "2B_runner", "3B_runner", "outs"])
        for k, v in plays.iteritems():
            game_id = k
            for p in v:
                writer.writerow([game_id]+p)

    with open('pitches.csv', 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["game_id", "pitcher", "pitch_number", "inning",
                         "top_bottom", "play_number", "pitch", "balls", "strikes"])
        for k, v in pitch_seq.iteritems():
            game_id = k
            for p, i in v.iteritems():
                for c in i:
                    writer.writerow([game_id]+[p]+c)

    with open('b_stats.csv', 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["game_id", "play_number", "pa", "ab", "h", "d", "t",
                         "hr", "rbi", "bb", "so", "gdp", "hbp", "sh", "sf",
                         "ibb"])
        for k, v in stats.iteritems():
            game_id = k
            b_s = v["batting_stats"]
            for st in b_s:
                writer.writerow([game_id] + [str(st.play_id),
                                             str(st.pa),
                                             str(st.ab),
                                             str(st.h),
                                             str(st.d),
                                             str(st.t),
                                             str(st.hr),
                                             str(st.rbi),
                                             str(st.bb),
                                             str(st.so),
                                             str(st.gdp),
                                             str(st.hbp),
                                             str(st.sh),
                                             str(st.sf),
                                             str(st.ibb)])


def main():
    for filename in sys.argv[1:]:
        print "Parsing " + filename
        parse_gamefiles(filename)
    print "Writing files"
    write_out(game_info, data, lineups, plays, stats)
    for k, v in stats.iteritems():
        print "Game: " + k
        o_s = v["other_stats"]
        for st in o_s:
            print ", ".join([str(st.play_number), st.player, st.stat])

main()
