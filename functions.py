#This file is responsible for all the functionality
from config import UserConfig
import mysql.connector
from colorama import init, Fore
import redis
import bcrypt
import datetime
import requests
from discord_webhook import DiscordWebhook, DiscordEmbed
import time
import hashlib 
import json
import pycountry
from osrparse import *
import os
from changelogs import Changelogs
import timeago

from lets_common_log import logUtils as log
from mods import mods
import smtplib
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import string
import random


init() #initialises colourama for colours
Changelogs.reverse()

print(fr"""{Fore.BLUE}  _____            _ _     _   _ _    _____                 _ _ 
 |  __ \          | (_)   | | (_) |  |  __ \               | | |
 | |__) |___  __ _| |_ ___| |_ _| | _| |__) |_ _ _ __   ___| | |
 |  _  // _ \/ _` | | / __| __| | |/ /  ___/ _` | '_ \ / _ \ | |
 | | \ \  __/ (_| | | \__ \ |_| |   <| |  | (_| | | | |  __/ |_|
 |_|  \_\___|\__,_|_|_|___/\__|_|_|\_\_|   \__,_|_| |_|\___|_(_)
 ---------------------------------------------------------------
{Fore.RESET}""")

log.warning("깃허브에 새 버전에서 buildinfo.json가 제거되어 업데이트 불가 현상으로, update.py의 기능 중지함.")
log.warning("Due to the phenomenon that buildinfo.json is removed from the new version on GitHub, update is not possible, and the function of update.py is stopped. \n")

#gotta def this here sorry
def ConsoleLog(Info: str, Additional: str="", Type: int=1):
    """Adds a log to the log file."""
    ### Types
    # 1 = Info
    # 2 = Warning
    # 3 = Error
    LogToAdd = {
        "Type": Type,
        "Info" : Info,
        "Extra" : Additional,
        "Timestamp" : round(time.time())
    }
    if not os.path.exists("realistikpanel.log"):
        #if doesnt exist
        with open("realistikpanel.log", "w+") as json_file:
            json.dump([], json_file, indent=4)
    
    #gets current log
    with open("realistikpanel.log", "r") as Log:
        Log = json.load(Log)

    Log.append(LogToAdd) #adds current log

    with open("realistikpanel.log", 'w') as json_file:
        json.dump(Log, json_file, indent=4)

    #webhook
    #first we get embed colour so it isnt mixed with the actual webhook
    if Type == 1: #this makes me wish python had native switch statements
        Colour = "4360181"
        TypeText = "log"
        Icon = "https://cdn3.iconfinder.com/data/icons/bold-blue-glyphs-free-samples/32/Info_Circle_Symbol_Information_Letter-512.png"
    if Type == 2:
        Colour = "16562691"
        TypeText = "warning"
        Icon = "https://icon2.cleanpng.com/20180626/kiy/kisspng-warning-sign-computer-icons-clip-art-warning-icon-5b31bd67368be5.4827407215299864072234.jpg"
    if Type == 3:
        Colour = "15417396"
        TypeText = "error"
        Icon = "https://freeiconshop.com/wp-content/uploads/edd/error-flat.png"
    
    #I promise to redo this, this is just proof of concept
    if UserConfig["ConsoleLogWebhook"] != "":
        webhook = DiscordWebhook(url=UserConfig["ConsoleLogWebhook"])
        embed = DiscordEmbed(description=f"{Info}\n{Additional}", color=Colour)
        embed.set_author(name=f"RealistikPanel {TypeText}!", icon_url=Icon)
        embed.set_footer(text="RealistikPanel Console Log")
        webhook.add_embed(embed)
        webhook.execute()


try:
    mydb = mysql.connector.connect(
        host=UserConfig["SQLHost"],
        port=UserConfig["SQLPort"],
        user=UserConfig["SQLUser"],
        passwd=UserConfig["SQLPassword"]
    ) #connects to database
    print(f"{Fore.GREEN} Successfully connected to MySQL!")
    mydb.autocommit = True
except Exception as e:
    print(f"{Fore.RED} Failed connecting to MySQL! Abandoning!\n Error: {e}{Fore.RESET}")
    ConsoleLog("Failed to connect to MySQL", f"{e}", 3)
    exit()

try:
    r = redis.Redis(host=UserConfig["RedisHost"], port=UserConfig["RedisPort"], password=UserConfig["RedisPassword"], db=UserConfig["RedisDb"]) #establishes redis connection
    print(f"{Fore.GREEN} Successfully connected to Redis!")
except Exception as e:
    print(f"{Fore.RED} Failed connecting to Redis! Abandoning!\n Error: {e}{Fore.RESET}")
    ConsoleLog("Failed to connect to Redis", f"{e}", 3)
    exit()

mycursor = mydb.cursor(buffered=True) #creates a thing to allow us to run mysql commands
mycursor.execute(f"USE {UserConfig['SQLDatabase']}") #Sets the db to ripple
mycursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")

#fix potential crashes
#have to do it this way as the crash issue is a connector module issue
mycursor.execute("SELECT COUNT(*) FROM users_stats WHERE userpage_content = ''")
BadUserCount = mycursor.fetchone()[0]
if BadUserCount > 0:
    print(f"{Fore.RED} Found {BadUserCount} users with potentially problematic data!{Fore.RESET}")
    print(" Fixing...", end="")#end = "" means it doesnt do a newline
    mycursor.execute("UPDATE users_stats SET userpage_content = NULL WHERE userpage_content = ''")
    mydb.commit()
    print(" Done!")

#public variables
PlayerCount = [] # list of players 
CachedStore = {}

def botch_sql_recovery() -> None:
    """Attepts to recreate the MySQL connection on fail. Currently the panel has
    VERY poor MySQL handling which leads to a lot of crashes. This is a really
    stupid fix that makes it so that the panel does not have to be restarted
    upon SQL doing the death. This is a REALLY botch fix, shouldnt exist."""

    global mycursor
    try:
        mycursor.close()
    except Exception: pass
    mycursor = mydb.cursor(buffered=True) #creates a thing to allow us to run mysql commands
    mycursor.execute(f"USE {UserConfig['SQLDatabase']}") #Sets the db to ripple
    mycursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")


def DashData():
    #note to self: add data caching so data isnt grabbed every time the dash is accessed
    """Grabs all the values for the dashboard."""
    mycursor.execute("SELECT value_string FROM system_settings WHERE name = 'website_global_alert'")
    Alert = mycursor.fetchall()
    if len(Alert) == 0:
        #some ps only have home alert
        mycursor.execute("SELECT value_string FROM system_settings WHERE name = 'website_home_alert'")
        #if also that doesnt exist
        Alert = mycursor.fetchall()
        if len(Alert) == 0:
            Alert = [[]]
    Alert = Alert[0][0]
    if Alert == "": #checks if no alert
        Alert = False

    totalPP = r.get("ripple:total_pp")#Not calculated by every server .decode("utf-8")
    RegisteredUsers = r.get("ripple:registered_users")
    OnlineUsers = r.get("ripple:online_users")
    TotalPlays = r.get("ripple:total_plays")
    TotalScores = r.get("ripple:total_submitted_scores")

    #If we dont have variable(variable is None) will set it and get it again
    if not totalPP:
        r.set('ripple:total_pp', 0)
        totalPP = r.get("ripple:total_pp")
    if not RegisteredUsers:
        r.set('ripple:registered_users', 1)
        RegisteredUsers = r.get("ripple:registered_users")
    if not OnlineUsers:
        r.set('ripple:online_users', 1)
        OnlineUsers = r.get("ripple:online_users")
    if not TotalPlays:
        r.set('ripple:total_plays', 1)
        TotalPlays = r.get("ripple:total_plays")
    if not TotalScores:
        r.set('ripple:total_submitted_scores', 1)
        TotalScores = r.get("ripple:total_submitted_scores")
    response = {
        "RegisteredUsers" : RegisteredUsers.decode("utf-8") ,
        "OnlineUsers" : OnlineUsers.decode("utf-8"),
        "TotalPP" : f'{int(totalPP.decode("utf-8")):,}',
        "TotalPlays" : f'{int(TotalPlays.decode("utf-8")):,}',
        "TotalScores" : f'{int(TotalScores.decode("utf-8")):,}',
        "Alert" : Alert
    }
    return response

def LoginHandler(username, password):
    """Checks the passwords and handles the sessions."""
    mycursor.execute("SELECT username, password_md5, ban_datetime, privileges, id FROM users WHERE username_safe = %s", (RippleSafeUsername(username),))
    User = mycursor.fetchall()
    if len(User) == 0:
        #when user not found
        return False, "The user was not found. Maybe you have made a typo?"
    else:
        User = User[0]
        #Stores grabbed data in variables for easier access
        Username = User[0]
        PassHash = User[1]
        IsBanned = User[2]
        Privilege = User[3]
        UserID = User[4]
        
        #dont  allow the bot account to log in (in case the server has a MASSIVE loophole)
        if UserID == 999:
            return [False, "You may not log into the bot account."]

        #shouldve been done during conversion but eh
        if not IsBanned == "0" or not IsBanned:
            return False, "It seems you have been banned... Yikes..."
        else:
            if HasPrivilege(UserID):
                if checkpw(PassHash, password):
                    return [True, "You have been logged in!", { #creating session
                        "LoggedIn" : True,
                        "AccountId" : UserID,
                        "AccountName" : Username,
                        "Privilege" : Privilege,
                        "exp" : datetime.datetime.utcnow() + datetime.timedelta(hours=2) #so the token expires
                    }]
                else:
                     return False, "The password you have entered is incorrect!"
            else:
                return False, "The account you are attempting to log into is missing the appropriate privileges to carry out this action!"

def TimestampConverter(timestamp, NoDate=2):
    """Converts timestamps into readable time."""
    date = datetime.datetime.fromtimestamp(int(timestamp)) #converting into datetime object
    date += datetime.timedelta(hours=UserConfig["TimezoneOffset"]) #adding timezone offset to current time
    #so we avoid things like 21:6
    #hour = str(date.hour)
    #minute = str(date.minute)
    #if len(hour) == 1:
        #hour = "0" + hour
    #if len(minute) == 1:
        #minute = "0" + minute
    if NoDate == 1:
        #return f"{hour}:{minute}"
        return date.strftime("%H:%M")
    if NoDate == 2:
        #return date.strftime("%H:%M %d/%m/%Y")
        return date.strftime("%Y/%m/%d/ %H:%M")

def RecentPlays(TotalPlays = 20, MinPP = 0):
    """Returns recent plays."""
    #this is probably really bad

    log.info("RecentPlays 함수 요청됨")

    """ DivBy = 1
    if UserConfig["HasRelax"]: DivBy += 1
    if UserConfig["HasAutopilot"]: DivBy += 1
    PerGamemode = round(TotalPlays/DivBy)
    mycursor.execute("SELECT scores.beatmap_md5, users.username, scores.userid, scores.time, scores.score, scores.pp, scores.play_mode, scores.mods, scores.300_count, scores.100_count, scores.50_count, scores.misses_count FROM scores LEFT JOIN users ON users.id = scores.userid WHERE users.privileges & 1 AND scores.pp >= %s ORDER BY scores.id DESC LIMIT %s", (MinPP, PerGamemode,))
    plays = mycursor.fetchall()
    if UserConfig["HasRelax"]:
        #adding relax plays
        mycursor.execute("SELECT scores_relax.beatmap_md5, users.username, scores_relax.userid, scores_relax.time, scores_relax.score, scores_relax.pp, scores_relax.play_mode, scores_relax.mods, scores_relax.300_count, scores_relax.100_count, scores_relax.50_count, scores_relax.misses_count FROM scores_relax LEFT JOIN users ON users.id = scores_relax.userid WHERE users.privileges & 1 AND scores_relax.pp >= %s ORDER BY scores_relax.id DESC LIMIT %s", (MinPP, PerGamemode,))
        playx_rx = mycursor.fetchall()
        for plays_rx in playx_rx:
            #addint them to the list
            plays_rx = list(plays_rx)
            plays.append(plays_rx)
    if UserConfig["HasAutopilot"]:
        #adding relax plays
        mycursor.execute("SELECT scores_ap.beatmap_md5, users.username, scores_ap.userid, scores_ap.time, scores_ap.score, scores_ap.pp, scores_ap.play_mode, scores_ap.mods, scores_ap.300_count, scores_ap.100_count, scores_ap.50_count, scores_ap.misses_count FROM scores_ap LEFT JOIN users ON users.id = scores_ap.userid WHERE users.privileges & 1 AND scores_ap.pp >= %s ORDER BY scores_ap.id DESC LIMIT %s", (MinPP, PerGamemode,))
        playx_ap = mycursor.fetchall()
        for plays_ap in playx_ap:
            #addint them to the list
            plays_ap = list(plays_ap)
            plays.append(plays_ap) """
    
    SQL = f"""
        SELECT 
            s.beatmap_md5,
            u.username,
            s.userid,
            s.time,
            s.score,
            s.pp,
            s.play_mode,
            s.mods,
            s.300_count,
            s.100_count,
            s.50_count,
            s.misses_count,
            s.id,
            s.completed,
            b.song_name,
            b.beatmap_id,
            b.beatmapset_id,
            b.ranked
        FROM (
            SELECT * FROM scores WHERE pp >= {MinPP}
            UNION ALL
            SELECT * FROM scores_relax WHERE pp >= {MinPP}
            UNION ALL
            SELECT * FROM scores_ap WHERE pp >= {MinPP}
        ) AS s
        LEFT JOIN users AS u ON u.id = s.userid
        LEFT JOIN (
            SELECT DISTINCT beatmap_md5, song_name, beatmap_id, beatmapset_id, ranked
            FROM beatmaps
        ) AS b ON b.beatmap_md5 = s.beatmap_md5
        WHERE u.privileges & 1
        ORDER BY s.time DESC
        LIMIT {TotalPlays}
    """

    mycursor.execute(SQL)
    plays = mycursor.fetchall()
    log.info(f"DB조회 완료! | len(plays) = {len(plays)}")

# 이제 sql_query 변수에는 예쁘게 정리된 SQL 쿼리 문자열이 들어 있습니다.


    #converting the data into something readable
    ReadableArray = []
    for x in plays:
        #yes im doing this
        #lets get the song name
        BeatmapMD5 = x[0]        
        SongName = x[14]

        if SongName is None:
            SongName = "Invalid..."
            log.error("SongName = {}".format(SongName))
            log.error("스코어 정보는 아래 표시 예정")

        #make and populate a readable dict
        Dicti = {}

        Dicti["Nodata"] = 0

        Mods = ModToText(x[7])
        if Mods == "":
            Dicti["SongName"] = SongName
        else:
            Dicti["SongName"] = SongName + " +" + Mods

        Dicti["Player"] = x[1]
        Dicti["PlayerId"] = x[2]
        Dicti["Score"] = f'{x[4]:,}'
        Dicti["pp"] = round(x[5], 2)
        Dicti["Timestamp"] = x[3]
        Dicti["Time"] = TimestampConverter(x[3])
        Dicti["Accuracy"] = round(GetAccuracy(x[8], x[9], x[10], x[11]), 2)
        Dicti["scoreID"] = x[12]
        Dicti["completed"] = x[13]

        try:
            if x[17] == 2:
                Dicti["ranked"] = ["Ranked", 2]
            elif x[17] == 5:
                Dicti["ranked"] = ["Loved", 5]
            elif x[17] == 3:
                Dicti["ranked"] = ["Approved", 3]
            elif x[17] == 4:
                Dicti["ranked"] = ["Qualified", 4]
            elif x[17] == 0:
                Dicti["ranked"] = ["Unranked", 0]
            elif x[17] is None:
                raise
        except:
            Dicti["ranked"] = ["Invalid...", 0]

        if SongName == "Invalid...":
            Dicti["Accuracy"] = f"Beatmap_md5 = {BeatmapMD5})  ({Dicti['Accuracy']}"

        if x[6] == 0:
            Dicti["gameMode"] = " [STD]"
        elif x[6] == 1:
            Dicti["gameMode"] = " [Taiko]"
        elif x[6] == 2:
            Dicti["gameMode"] = " [CTB]"
        elif x[6] == 3:
            Dicti["gameMode"] = " [Mania]"
        else:
            Dicti["gameMode"] = " []"
        
        try:
            Dicti["beatmapID"] = x[15]
            if x[15] is None:
                raise
        except:
            log.error(x)
            Dicti["Nodata"] += 1
            Dicti["beatmapID"] = BeatmapMD5
            Dicti["Nodata_SongName"] = SongName

        ReadableArray.append(Dicti)
    
    #ReadableArray = sorted(ReadableArray, key=lambda k: k["Timestamp"]) #sorting by time
    #ReadableArray.reverse()
    return ReadableArray

def FetchBSData():
    """Fetches Bancho Settings."""
    mycursor.execute("SELECT name, value_string, value_int FROM bancho_settings WHERE name = 'bancho_maintenance' OR name = 'menu_icon' OR name = 'login_notification'")
    Query = list(mycursor.fetchall())
    #bancho maintenence
    if Query[0][2] == 0:
        BanchoMan = False
    else:
        BanchoMan = True
    return {
        "BanchoMan" : BanchoMan,
        "MenuIcon" : Query[1][1],
        "LoginNotif" : Query[2][1]
    }

def BSPostHandler(post, session):
    BanchoMan = post[0]
    MenuIcon = post[1]
    LoginNotif = post[2]

    #setting blanks to bools
    if BanchoMan == "On":
        BanchoMan = True
    else:
        BanchoMan = False
    if MenuIcon == "":
        MenuIcon = False
    if LoginNotif == "":
        LoginNotif = False

    #SQL Queries
    if MenuIcon != False: #this might be doable with just if not BanchoMan
        mycursor.execute("UPDATE bancho_settings SET value_string = %s, value_int = 1 WHERE name = 'menu_icon'", (MenuIcon,))
    else:
        mycursor.execute("UPDATE bancho_settings SET value_string = '', value_int = 0 WHERE name = 'menu_icon'")

    if LoginNotif != False:
        mycursor.execute("UPDATE bancho_settings SET value_string = %s, value_int = 1 WHERE name = 'login_notification'", (LoginNotif,))
    else:
        mycursor.execute("UPDATE bancho_settings SET value_string = '', value_int = 0 WHERE name = 'login_notification'")

    if BanchoMan:
        mycursor.execute("UPDATE bancho_settings SET value_int = 1 WHERE name = 'bancho_maintenance'")
    else:
        mycursor.execute("UPDATE bancho_settings SET value_int = 0 WHERE name = 'bancho_maintenance'")
    
    mydb.commit()
    RAPLog(session["AccountId"], "modified the bancho settings")

def GetBmapInfo(id):
    """Gets beatmap info."""
    mycursor.execute("SELECT beatmapset_id FROM beatmaps WHERE beatmap_id = %s", (id,))
    Data = mycursor.fetchall()
    if len(Data) == 0:
        #it might be a beatmap set then
        mycursor.execute("SELECT song_name, ar, difficulty_std, beatmapset_id, beatmap_id, ranked FROM beatmaps WHERE beatmapset_id = %s", (id,))
        BMS_Data = mycursor.fetchall()
        if len(BMS_Data) == 0: #if still havent found anything

            return [{
                "SongName" : "Not Found",
                "Ar" : "0",
                "Difficulty" : "0",
                "BeatmapsetId" : "",
                "BeatmapId" : 0,
                #rankedby 추가
                "Rankedby" : "",
                "Cover" : "https://a.redstar.moe/" #why this%s idk
            }]
    else:
        BMSID = Data[0][0]
        mycursor.execute("SELECT song_name, ar, difficulty_std, beatmapset_id, beatmap_id, ranked FROM beatmaps WHERE beatmapset_id = %s", (BMSID,))
        BMS_Data = mycursor.fetchall()

    BeatmapList = []

    for beatmap in BMS_Data:

        mycursor.execute("SELECT rankedby FROM beatmaps WHERE beatmap_id = %s", (str(beatmap[4]),))
        rankedby = mycursor.fetchall()
        log.info("BeatmapID = {}, rankedby = {}".format(str(beatmap[4]), rankedby[0][0]))

        thing = { 
            "SongName" : beatmap[0],
            "Ar" : str(beatmap[1]),
            "Difficulty" : str(round(beatmap[2], 2)),
            "BeatmapsetId" : str(beatmap[3]),
            "BeatmapId" : str(beatmap[4]),
            "Ranked" : beatmap[5],
            #rankedby 추가
            "Rankedby" : rankedby[0][0],
            "Cover" : f"https://b.redstar.moe/bg/{beatmap[4]}"
            #"Cover" : f"https://assets.ppy.sh/beatmaps/{beatmap[3]}/covers/cover.jpg"
        }
        
        BeatmapList.append(thing)
    BeatmapList =  sorted(BeatmapList, key = lambda i: i["Difficulty"])
    #assigning each bmap a number to be later used
    BMapNumber = 0
    for beatmap in BeatmapList:
        BMapNumber = BMapNumber + 1
        beatmap["BmapNumber"] = BMapNumber
    return BeatmapList

def HasPrivilege(UserID : int, ReqPriv = 2):
    """Check if the person trying to access the page has perms to do it."""
    #tbh i shouldve done it where you pass the priv enum instead

    # 0 = no verification
    # 1 = Only registration required
    # 2 = RAP Access Required
    # 3 = Manage beatmaps required
    # 4 = manage settings required
    # 5 = Ban users required
    # 6 = Manage users required
    # 7 = View logs
    # 8 = RealistikPanel Nominate (feature not added yet)
    # 9 = RealistikPanel Nomination Accept (feature not added yet)
    # 10 = RealistikPanel Overwatch (feature not added yet)
    # 11 = Wipe account required
    # 12 = Kick users required
    # 13 = Manage Privileges
    # 14 = View RealistikPanel error/console logs
    # 15 = Manage Clans (RealistikPanel specific permission)
    # 16 = View IPs in manage users
    #THIS TOOK ME SO LONG TO FIGURE OUT WTF
    NoPriv = 0
    UserNormal = 2 << 0
    AccessRAP = 2 << 2
    ManageUsers = 2 << 3
    BanUsers = 2 << 4
    SilenceUsers = 2 << 5
    WipeUsers = 2 << 6
    ManageBeatmaps = 2 << 7
    ManageServers = 2 << 8
    ManageSettings = 2 << 9
    ManageBetaKeys = 2 << 10
    ManageReports = 2 << 11
    ManageDocs = 2 << 12
    ManageBadges = 2 << 13
    ViewRAPLogs	= 2 << 14
    ManagePrivileges = 2 << 15
    SendAlerts = 2 << 16
    ChatMod	 = 2 << 17
    KickUsers = 2 << 18
    PendingVerification = 2 << 19
    TournamentStaff  = 2 << 20
    Caker = 2 << 21
    ViewTopScores = 2 << 22
    #RealistikPanel Specific Perms
    RPNominate = 2 << 23
    RPNominateAccept = 2 << 24
    RPOverwatch = 2 << 25
    RPErrorLogs = 2 << 26
    RPManageClans = 2 << 27
    RPViewIPs = 2 << 28

    if ReqPriv == 0: #dont use this like at all
        return True

    #gets users privilege
    mycursor.execute("SELECT privileges FROM users WHERE id = %s", (UserID,))
    Privilege = mycursor.fetchall()
    if len(Privilege) == 0:
        Privilege = 0
    else:
        Privilege = Privilege[0][0]

    if ReqPriv == 1:
        result = Privilege & UserNormal
    elif ReqPriv == 2:
        result = Privilege & AccessRAP
    elif ReqPriv == 3:
        result = Privilege & ManageBeatmaps
    elif ReqPriv == 4:
        result = Privilege & ManageSettings
    elif ReqPriv == 5:
        result = Privilege & BanUsers
    elif ReqPriv == 6:
        result = Privilege & ManageUsers
    elif ReqPriv == 7:
        result = Privilege & ViewRAPLogs
    elif ReqPriv == 8:
        result = Privilege & RPNominate
    elif ReqPriv == 9:
        result = Privilege & RPNominateAccept
    elif ReqPriv == 10:
        result = Privilege & RPOverwatch
    elif ReqPriv == 11:
        result = Privilege & WipeUsers
    elif ReqPriv == 12:
        result = Privilege & KickUsers
    elif ReqPriv == 13:
        result = Privilege & ManagePrivileges
    elif ReqPriv == 14:
        result = Privilege & RPErrorLogs
    elif ReqPriv == 15:
        result = Privilege & RPManageClans
    elif ReqPriv == 16:
        result = Privilege & RPViewIPs
    
    if result >= 1:
        return True
    else:
        return False
    

def RankBeatmap(BeatmapNumber, BeatmapId, ActionName, session):
    """Ranks a beatmap"""
    #converts actions to numbers
    if ActionName == "Loved":
        ActionName = 5
    elif ActionName == "Ranked":
        ActionName = 2
    elif ActionName == "Unranked":
        ActionName = 0
    elif ActionName == "Approved":
        ActionName = 3
    elif ActionName == "Qualified":
        ActionName = 4
    else:
        print(" Received alien input from rank. what?")
        return

    mycursor.execute("SELECT ranked FROM beatmaps WHERE beatmap_id = %s", (BeatmapId,))
    oldRank = mycursor.fetchone()[0]
    mycursor.execute("UPDATE beatmaps SET ranked = %s, ranked_status_freezed = 1 WHERE beatmap_id = %s LIMIT 1", (ActionName, BeatmapId,))
    #mycursor.execute("UPDATE scores s JOIN (SELECT userid, MAX(score) maxscore FROM scores JOIN beatmaps ON scores.beatmap_md5 = beatmaps.beatmap_md5 WHERE beatmaps.beatmap_md5 = (SELECT beatmap_md5 FROM beatmaps WHERE beatmap_id = %s LIMIT 1) GROUP BY userid) s2 ON s.score = s2.maxscore AND s.userid = s2.userid SET completed = 3", (BeatmapId,))
    mydb.commit()
    Webhook(BeatmapId, ActionName, session, oldRank)

def FokaMessage(params) -> None:
    """Sends a fokabot message."""
    requests.get(f"{UserConfig['BanchoURL']}api/v1/fokabotMessage", params=params)

def Webhook(BeatmapId, ActionName, session, oldRank):
    """Beatmap rank webhook."""

    mycursor.execute("SELECT difficulty_std, difficulty_taiko, difficulty_ctb, difficulty_mania FROM beatmaps WHERE beatmap_id = %s", (BeatmapId,))
    mode = mycursor.fetchall()

    URL = UserConfig["Webhook-std"]

    isskip = 0
    #모든 모드난이도가 0일때 거르는 코드
    if isskip == 0 and mode[0][0] == 0 and mode[0][1] == 0 and mode[0][2] == 0 and mode[0][3] == 0:
        URL = UserConfig["Webhook-std"]
        log.warning("모든 모드의 난이도가 0임, BeatmapID = {}".format(BeatmapId))
        log.warning("DB에서 {} 비트맵 데이터 삭제.".format(BeatmapId))
        mycursor.execute("DELETE FROM beatmaps WHERE beatmap_id = %s", (BeatmapId,))
        mydb.commit()
        isskip = 1
    #std
    if isskip == 0 and mode[0][0] != 0:
        mode = 0
        URL = UserConfig["Webhook-std"]
        isskip = 1
    #Taiko
    if isskip == 0 and mode[0][0] == 0 and mode[0][1] != 0:
        mode = 1
        URL = UserConfig["Webhook-taiko"]
        isskip = 1
    #ctb
    if isskip == 0 and mode[0][0] == 0 and mode[0][2] != 0:
        mode = 2
        URL = UserConfig["Webhook-ctb"]
        isskip = 1
    #Mania
    if isskip == 0 and mode[0][0] == 0 and mode[0][3] != 0:
        mode = 3
        URL = UserConfig["Webhook-mania"]
        isskip = 1
    
    log.chat("Beatmap, mode = {}, URL = {}".format(mode, URL))
    #URL = UserConfig["Webhook"]
    if URL == "":
        #if no webhook is set, dont do anything
        return
    mycursor.execute("SELECT song_name, beatmapset_id difficulty_std FROM beatmaps WHERE beatmap_id = %s", (BeatmapId,))
    mapa = mycursor.fetchall()
    mapa = mapa[0]
    if ActionName == 0:
        TitleText = "unranked..."
    if ActionName == 2:
        TitleText = "ranked!"
    if ActionName == 5:
        TitleText = "loved!"
    if ActionName == 3:
        TitleText = "Approved!"
    if ActionName == 4:
        TitleText = "Qualified!"

    if oldRank == 0:
        oldRank = "unranked..."
    if oldRank == 2:
        oldRank = "ranked!"
    if oldRank == 5:
        oldRank = "loved!"
    if oldRank == 3:
        oldRank = "Approved!"
    if oldRank == 4:
        oldRank = "Qualified!"

    webhook = DiscordWebhook(url=URL) #creates webhook
    # me trying to learn the webhook
    #EmbedJson = { #json to be sent to webhook
    #    "image" : f"https://assets.ppy.sh/beatmaps/{mapa[1]}/covers/cover.jpg",
    #    "author" : {
    #        "icon_url" : f"https://a.ussr.pl/{session['AccountId']}",
    #        "url" : f"https://ussr.pl/b/{BeatmapId}",
    #        "name" : f"{mapa[0]} was just {TitleText}"
    #    },
    #    "description" : f"Ranked by {session['AccountName']}",
    #    "footer" : {
    #        "text" : "via RealistikPanel!"
    #    }
    #}
    #requests.post(URL, data=EmbedJson, headers=headers) #sends the webhook data
    embed = DiscordEmbed(description=f"Status Changed by {session['AccountName']}", color=242424) #this is giving me discord.py vibes
    embed.set_author(name=f"{mapa[0]} was just {oldRank} --> {TitleText} (Beatmap)", url=f"{UserConfig['ServerURL']}b/{BeatmapId}", icon_url=f"{UserConfig['AvatarServer']}{session['AccountId']}")
    embed.set_footer(text="via RealistikPanel!")
    #embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{mapa[1]}/covers/cover.jpg")
    embed.set_image(url=f"https://b.redstar.moe/bg/{BeatmapId}")
    webhook.add_embed(embed)
    print(" * Posting webhook!")
    webhook.execute()
    if ActionName == 0:
        Logtext = "unranked"
    if ActionName == 2:
        Logtext = "ranked"
    if ActionName == 5:
        Logtext = "loved"
    if ActionName == 3:
        Logtext = "Approved"
    if ActionName == 4:
        Logtext = "Qualified"

    RAPLog(session["AccountId"], f"{Logtext} the beatmap {mapa[0]} ({BeatmapId})")
    #ingamemsg = f"[https://{UserConfig['ServerURL']}u/{session['AccountId']} {session['AccountName']}] {Logtext.lower()} the map [https://redstar.moe/b/{BeatmapId} {mapa[0]}]  [osu://dl/{mapa[1]} osu!direct]"
    ingamemsg = f"[{UserConfig['ServerURL']}u/{session['AccountId']} {session['AccountName']}] {Logtext.lower()} the map [https://osu.redstar.moe/b/{BeatmapId} {mapa[0]}]  [osu://b/{BeatmapId} osu!direct]"
    params = {"k": UserConfig['FokaKey'], "to": "#ranked", "msg": ingamemsg}
    FokaMessage(params)

def RAPLog(UserID=999, Text="forgot to assign a text value :/"):
    """Logs to the RAP log."""
    Timestamp = round(time.time())
    #now we putting that in oh yea
    mycursor.execute("INSERT INTO rap_logs (userid, text, datetime, through) VALUES (%s, %s, %s, 'RealistikPanel!')", (UserID, Text, Timestamp,))
    mydb.commit()
    #webhook time
    if UserConfig["AdminLogWebhook"] != "":
        Username = GetUser(UserID)["Username"]
        webhook = DiscordWebhook(UserConfig["AdminLogWebhook"])
        embed = DiscordEmbed(description=f"{Username} {Text}", color=242424)
        embed.set_footer(text="RealistikPanel Admin Logs")
        embed.set_author(name=f"New action done by {Username}!", url=f"{UserConfig['ServerURL']}u/{UserID}", icon_url = f"{UserConfig['AvatarServer']}{UserID}")
        webhook.add_embed(embed)
        webhook.execute()

def checkpw(dbpassword, painpassword):
    """
    By: kotypey
    password checking...
    """

    result = hashlib.md5(painpassword.encode()).hexdigest().encode('utf-8')
    dbpassword = dbpassword.encode('utf-8')
    check = bcrypt.checkpw(result, dbpassword)

    return check

def SystemSettingsValues():
    """Fetches the system settings data."""
    mycursor.execute("SELECT value_int, value_string FROM system_settings WHERE name = 'website_maintenance' OR name = 'game_maintenance' OR name = 'website_global_alert' OR name = 'website_home_alert' OR name = 'registrations_enabled'")
    SqlData = mycursor.fetchall()
    return {
        "webman": bool(SqlData[0][0]),
        "gameman" : bool(SqlData[1][0]),
        "register": bool(SqlData[4][0]),
        "globalalert": SqlData[2][1],
        "homealert": SqlData[3][1]
    }

def ApplySystemSettings(DataArray, Session):
    """Applies system settings."""
    WebMan = DataArray[0]
    GameMan =DataArray[1]
    Register = DataArray[2]
    GlobalAlert = DataArray[3]
    HomeAlert = DataArray[4]

    #i dont feel like this is the right way to do this but eh
    if WebMan == "On":
        WebMan = 1
    else:
        WebMan = 0
    if GameMan == "On":
        GameMan = 1
    else:
        GameMan = 0
    if Register == "On":
        Register = 1
    else:
        Register = 0
    
    #SQL Queries
    mycursor.execute("UPDATE system_settings SET value_int = %s WHERE name = 'website_maintenance'", (WebMan,))
    mycursor.execute("UPDATE system_settings SET value_int = %s WHERE name = 'game_maintenance'", (GameMan,))
    mycursor.execute("UPDATE system_settings SET value_int = %s WHERE name = 'registrations_enabled'", (Register,))

    #if empty, disable
    if GlobalAlert != "":
        mycursor.execute("UPDATE system_settings SET value_int = 1, value_string = %s WHERE name = 'website_global_alert'", (GlobalAlert,))
    else:
        mycursor.execute("UPDATE system_settings SET value_int = 0, value_string = '' WHERE name = 'website_global_alert'")
    if HomeAlert != "":
        mycursor.execute("UPDATE system_settings SET value_int = 1, value_string = %s WHERE name = 'website_home_alert'", (HomeAlert,))
    else:
        mycursor.execute("UPDATE system_settings SET value_int = 0, value_string = '' WHERE name = 'website_home_alert'")
    
    mydb.commit() #applies the changes

def IsOnline(AccountId: int) -> bool:
    """Checks if given user is online."""
    try:
        Online = requests.get(url=f"{UserConfig['BanchoURL']}api/v1/isOnline?id={AccountId}").json()
        if Online["status"] == 200:
            return Online["result"]
        else:
            return False
    except Exception: return False

def CalcPP(BmapID):
    """Sends request to letsapi to calc PP for beatmap id."""
    reqjson = requests.get(url=f"{UserConfig['LetsAPI']}v1/pp?b={BmapID}").json()
    return round(reqjson["pp"][0], 2)

def CalcPPDT(BmapID):
    """Sends request to letsapi to calc PP for beatmap id with the double time mod."""
    reqjson = requests.get(url=f"{UserConfig['LetsAPI']}v1/pp?b={BmapID}&m=64").json()
    return round(reqjson["pp"][0], 2)

def Unique(Alist):
    """Returns list of unique elements of list."""
    Uniques = []
    for x in Alist:
        if x not in Uniques:
            Uniques.append(x)
    return Uniques

def FetchUsers(page = 0):
    """Fetches users for the users page."""
    #This is going to need a lot of patching up i can feel it
    Offset = UserConfig["PageSize"] * page #for the page system to work
    mycursor.execute("SELECT id, username, privileges, allowed FROM users LIMIT %s OFFSET %s", (UserConfig['PageSize'], Offset,))
    People = mycursor.fetchall()

    #gets list of all different privileges so an sql select call isnt ran per person
    AllPrivileges = []
    for person in People:
        AllPrivileges.append(person[2])
    UniquePrivileges = Unique(AllPrivileges)

    #How the privilege data will look
    #PrivilegeDict = {
    #    "234543": {
    #        "Name" : "Owner",
    #        "Privileges" : 234543,
    #        "Colour" : "success"
    #    }
    #}
    PrivilegeDict = {}
    #gets all priv info
    for Priv in UniquePrivileges:
        mycursor.execute("SELECT name, color FROM privileges_groups WHERE privileges = %s LIMIT 1", (Priv,))
        info = mycursor.fetchall()
        if len(info) == 0:
            PrivilegeDict[str(Priv)] = {
                "Name" : f"Unknown ({Priv})",
                "Privileges" : Priv,
                "Colour" : "danger"
            }
        else:
            info = info[0]
            PrivilegeDict[str(Priv)] = {}
            PrivilegeDict[str(Priv)]["Name"] = info[0]
            PrivilegeDict[str(Priv)]["Privileges"] = Priv
            PrivilegeDict[str(Priv)]["Colour"] = info[1]
            if PrivilegeDict[str(Priv)]["Colour"] == "default" or PrivilegeDict[str(Priv)]["Colour"] == "":
                #stisla doesnt have a default button so ill hard-code change it to a warning
                PrivilegeDict[str(Priv)]["Colour"] = "warning"

    #Convierting user data into cool dicts
    #Structure
    #[
    #    {
    #        "Id" : 999,
    #        "Name" : "RealistikDash",
    #        "Privilege" : PrivilegeDict["234543"],
    #        "Allowed" : True
    #    }
    #]
    Users = []
    for user in People:
        #country query
        mycursor.execute("SELECT country FROM users_stats WHERE id = %s", (user[0],))
        Country = mycursor.fetchall()
        if len(Country) == 0:
            Country = "XX"
        else:
            Country = Country[0][0]
        Dict = {
            "Id" : user[0],
            "Name" : user[1],
            "Privilege" : PrivilegeDict[str(user[2])],
            "Country" : Country
        }
        if user[3] == 1:
            Dict["Allowed"] = True
        else:
            Dict["Allowed"] = False
        Users.append(Dict)
    
    return Users

def GetUser(id):
    """Gets data for user. (universal)"""
    mycursor.execute("SELECT id, username, pp_std, country FROM users_stats WHERE id = %s LIMIT 1", (id,))
    User = mycursor.fetchone()
    if User == None:
        #if no one found
        return {
            "Id" : 0,
            "Username" : "Not Found",
            "pp" : 0,
            "IsOnline" : False,
            "Country" : "GB" #RULE BRITANNIA
        }
    return {
        "Id" : User[0],
        "Username" : User[1],
        "pp" : User[2],
        "IsOnline" : IsOnline(id),
        "Country" : User[3]
    }

def UserData(UserID):
    """Gets data for user (specialised for user edit page)."""
    #fix badbad data
    mycursor.execute("UPDATE users_stats SET userpage_content = NULL WHERE userpage_content = '' AND id = %s", (UserID,))
    mydb.commit()
    Data = GetUser(UserID)
    mycursor.execute("SELECT userpage_content, user_color, username_aka FROM users_stats WHERE id = %s LIMIT 1", (UserID,))# Req 1
    Data1 = mycursor.fetchone()
    mycursor.execute("SELECT email, register_datetime, privileges, notes, donor_expire, silence_end, silence_reason, ban_datetime FROM users WHERE id = %s LIMIT 1", (UserID,))
    Data2 = mycursor.fetchone()
    #Fetches the IP
    mycursor.execute("SELECT ip FROM ip_user WHERE userid = %s LIMIT 1", (UserID,))
    Ip = mycursor.fetchone()
    if Ip == None:
        Ip = "0.0.0.0"
    else:
        Ip = Ip[0]
    #gets privilege name
    mycursor.execute("SELECT name FROM privileges_groups WHERE privileges = %s LIMIT 1", (Data2[2],))
    PrivData = mycursor.fetchone()
    if PrivData == None:
        PrivData = [[f"Unknown ({Data2[2]})"]]
    #adds new info to dict
    #I dont use the discord features from RAP so i didnt include the discord settings but if you complain enough ill add them
    try:
        mycursor.execute("SELECT freezedate FROM users WHERE id = %s LIMIT 1", (UserID,))
        Freeze = mycursor.fetchone()
    except:
        Freeze = False
  
    Data["UserpageContent"] = Data1[0]
    Data["UserColour"] = Data1[1]
    Data["Aka"] = Data1[2]
    Data["Email"] = Data2[0]
    Data["RegisterTime"] = Data2[1]
    Data["Privileges"] = Data2[2]
    Data["Notes"] = Data2[3]
    Data["DonorExpire"] = Data2[4]
    Data["SilenceEnd"] = Data2[5]
    Data["SilenceReason"] = Data2[6]
    Data["Avatar"] = UserConfig["AvatarServer"] + str(UserID)
    Data["Ip"] = Ip
    Data["CountryFull"] = GetCFullName(Data["Country"])
    Data["PrivName"] = PrivData[0]

    Data["HasSupporter"] = Data["Privileges"] & 4
    Data["DonorExpireStr"] = TimeToTimeAgo(Data["DonorExpire"])

    #now for silences and ban times
    Data["IsBanned"] = CoolerInt(Data2[7]) > 0                       
    Data["BanedAgo"] = TimeToTimeAgo(CoolerInt(Data2[7]))
    Data["IsSilenced"] =  CoolerInt(Data2[5]) > round(time.time())
    Data["SilenceEndAgo"] = TimeToTimeAgo(CoolerInt(Data2[5]))
    if Freeze:
        Data["IsFrozen"] = int(Freeze[0]) > 0
        Data["FreezeDateNo"] = int(Freeze[0])
        Data["FreezeDate"] = TimeToTimeAgo(Data["FreezeDateNo"])  
    else:
        Data["IsFrozen"] = False

    #removing "None" from user page and admin notes
    if Data["Notes"] == None:
        Data["Notes"] = ""
    if Data["UserpageContent"] == None:
        Data["UserpageContent"] = ""
    return Data

def RAPFetch(page = 1):
    """Fetches RAP Logs."""
    page = int(page) - 1 #makes sure is int and is in ok format
    Offset = UserConfig["PageSize"] * page
    mycursor.execute("SELECT * FROM rap_logs ORDER BY id DESC LIMIT %s OFFSET %s", (UserConfig['PageSize'], Offset,))
    Data = mycursor.fetchall()

    #Gets list of all users
    Users = []
    for dat in Data:
        if dat[1] not in Users:
            Users.append(dat[1])
    #gets all unique users so a ton of lookups arent made
    UniqueUsers = Unique(Users)

    #now we get basic data for each user
    UserDict = {}
    for user in UniqueUsers:
        UserData = GetUser(user)
        UserDict[str(user)] = UserData
    
    #log structure
    #[
    #    {
    #        "LogId" : 1337,
    #        "AccountData" : 1000,
    #        "Text" : "did a thing",
    #        "Via" : "RealistikPanel",
    #        "Time" : 18932905234
    #    }
    #]
    LogArray = []
    for log in Data:
        #we making it into cool dicts
        #getting the acc data
        LogUserData = UserDict[str(log[1])]
        TheLog = {
            "LogId" : log[0],
            "AccountData" : LogUserData,
            "Text" : log[2],
            "Time" : TimestampConverter(log[3], 2),
            "Via" : log[4]
        }
        LogArray.append(TheLog)
    return LogArray

def GetCFullName(ISO3166):
    """Gets the full name of the country provided."""
    Country = pycountry.countries.get(alpha_2=ISO3166)
    try:
        CountryName = Country.name
    except:
        CountryName = "Unknown"
    return CountryName

def GetPrivileges():
    """Gets list of privileges."""
    mycursor.execute("SELECT * FROM privileges_groups")
    priv = mycursor.fetchall()
    if len(priv) == 0:
        return []
    Privs = []
    for x in priv:
        Privs.append({
            "Id" : x[0],
            "Name" : x[1],
            "Priv" : x[2],
            "Colour" : x[3]
        })
    return Privs

def ApplyUserEdit(form, session):
    """Apples the user settings."""
    #getting variables from form
    UserId = int(form.get("userid", False))
    Username = form.get("username", False)
    Aka = form.get("aka", False)
    Email = form.get("email", False)
    Country = form.get("country", False)
    UserPage = form.get("userpage", False)
    Notes = form.get("notes", False)
    Privilege = form.get("privilege", False)
    if not UserId or not Username:
        print("Yo you seriously messed up the form")
        raise NameError
    #Creating safe username
    SafeUsername = RippleSafeUsername(Username)

    #fixing crash bug
    if UserPage == "":
        UserPage = None

    #stop people ascending themselves
    #OriginalPriv = int(session["Privilege"])
    FromID = session["AccountId"]
    if int(UserId) == FromID:
        mycursor.execute("SELECT privileges FROM users WHERE id = %s", (FromID,))
        OriginalPriv = mycursor.fetchall()
        if len(OriginalPriv) == 0:
            return
        OriginalPriv = OriginalPriv[0][0]
        if int(Privilege) > OriginalPriv:
            return

    #Badges

    BadgeList = [int(form.get("Badge1", 0)), int(form.get("Badge2", 0)), int(form.get("Badge3", 0)), int(form.get("Badge4", 0)), int(form.get("Badge5", 0)), int(form.get("Badge6", 0)), int(form.get("Badge7", 0)), int(form.get("Badge8", 0)), int(form.get("Badge9", 0)), int(form.get("Badge10", 0))]
    SetUserBadges(UserId, BadgeList)
    #SQL Queries
    mycursor.execute("UPDATE users SET email = %s, notes = %s, username = %s, username_safe = %s, privileges=%s WHERE id = %s", (Email, Notes, Username, SafeUsername,Privilege, UserId,))
    mycursor.execute("UPDATE users_stats SET country = %s, userpage_content = %s, username_aka = %s, username = %s WHERE id = %s", (Country, UserPage, Aka, Username, UserId,))
    if UserConfig["HasRelax"]:
        mycursor.execute("UPDATE rx_stats SET country = %s, username_aka = %s, username = %s WHERE id = %s", (Country, Aka, Username, UserId,))
    if UserConfig["HasAutopilot"]:
        mycursor.execute("UPDATE ap_stats SET country = %s, username_aka = %s, username = %s WHERE id = %s", (Country, Aka, Username, UserId,))
    mydb.commit()

    # Refresh in pep.py - Rosu only
    r.publish("peppy:refresh_privs", {
        "user_id": UserId
    })

    #hw_user 추가
    hw_mac = form.get("hw_mac")
    hw_unique_id = form.get("hw_unique_id")
    hw_disk_id = form.get("hw_disk_id")
    hw_activated = form.get("hw_activated")
    mycursor.execute(f"UPDATE hw_user SET mac = '{hw_mac}', unique_id = '{hw_unique_id}', disk_id = '{hw_disk_id}', activated = '{hw_activated}' WHERE userid = {UserId}")
    mydb.commit()

def ModToText(mod: int):
    """Converts mod enum to cool string."""
    #mod enums
    Mods = ""
    if mod == 0:
        return ""
    else:
        #adding mod names to str
        #they use bitwise too just like the perms
        """ if mod & 1:
            Mods += "NF"
        if mod & 2:
            Mods += "EZ"
        if mod & 4:
            Mods += "NV"
        if mod & 8:
            Mods += "HD"
        if mod & 16:
            Mods += "HR"
        if mod & 32:
            Mods += "SD"
        if mod & 512:
            Mods += "NC"
        elif mod & 64:
            Mods += "DT"
        if mod & 128:
            Mods += "RX"
        if mod & 256:
            Mods += "HT"
        if mod & 1024:
            Mods += "FL"
        if mod & 2048:
            Mods += "AO"
        if mod & 4096:
            Mods += "SO"
        if mod & 8192:
            Mods += "AP"
        if mod & 16384:
            Mods += "PF"
        if mod & 32768:
            Mods += "K4"
        if mod & 65536:
            Mods += "K5"
        if mod & 131072:
            Mods += "K6"
        if mod & 262144:
            Mods += "K7"
        if mod & 524288:
            Mods += "K8"
        if mod & 1015808:
            Mods += "KM" #idk what this is
        if mod & 1048576:
            Mods += "FI"
        if mod & 2097152:
            Mods += "RM"
        if mod & 4194304:
            Mods += "LM"
        if mod & 16777216:
            Mods += "K9"
        if mod & 33554432:
            Mods += "KX" #key 10 but 2 char. might change to k10
        if mod & 67108864:
            Mods += "K1"
        if mod & 134217728:
            #Mods += "K2"
            Mods += "K3"
        if mod & 268435456:
            #Mods += "K3"
            Mods += "K2"
        if mod & 536870912:
            Mods += "SV2(V2)"
        if mod & 1073741824:
            Mods += "MR" """

        if mod & mods.NOFAIL> 0:
            Mods += "NF"
        if mod & mods.EASY > 0:
            Mods += "EZ"
        if mod & mods.TOUCHSCREEN > 0:
            Mods += "TD(NV)"
        if mod & mods.HIDDEN > 0:
            Mods += "HD"
        if mod & mods.HARDROCK > 0:
            Mods += "HR"
        if mod & mods.SUDDENDEATH > 0:
            Mods += "SD"
        if mod & mods.DOUBLETIME > 0:
            Mods += "DT"
        if mod & mods.HALFTIME > 0:
            Mods += "HT"
        #NC 추가
        #576 = DT, NC
        if mod == 576 or  mod & mods.NIGHTCORE > 0:
            Mods = Mods.replace('DT', 'NC')
            #r += "NC, "
        if mod & mods.FLASHLIGHT > 0:
            Mods += "FL"
        if mod & mods.SPUNOUT > 0:
            Mods += "SO"
        #모드 추가
        if mod & mods.PERFECT > 0:
            Mods += "PF"
        #?????
        if mod & mods.RELAX > 0:
            Mods += "RX"
        if mod & mods.RELAX2 > 0:
            Mods += "AP"
        if mod & mods.KEY4 > 0:
            Mods += "K4"
        if mod & mods.KEY5 > 0:
            Mods += "K5"
        if mod & mods.KEY6 > 0:
            Mods += "K6"
        if mod & mods.KEY7 > 0:
            Mods += "K7"
        if mod & mods.KEY8 > 0:
            Mods += "K8"
        #?
        """ if __mods & mods.KEYMOD > 0:
            Mods += "KEYMOD" """
        if mod & mods.FADEIN > 0:
            Mods += "FI"
        if mod & mods.RANDOM > 0:
            Mods += "RD"
        #?
        """ if __mods & mods.LASTMOD > 0:
            Mods += "LASTMOD" """
        if mod & mods.KEY9 > 0:
            Mods += "K9"
        if mod & mods.KEY10 > 0:
            Mods += "KX(K10)"
        if mod & mods.KEY1 > 0:
            Mods += "K1"
        if mod & mods.KEY3 > 0:
            Mods += "K3"
        if mod & mods.KEY2 > 0:
            Mods += "K2"
        if mod & mods.SCOREV2 > 0:
            Mods += "SV2(v2)"
        if mod & mods.MIRROR > 0:
            Mods += "MR"

        return Mods

def WipeAccount(AccId):
    """Wipes the account with the given id."""
    r.publish("peppy:disconnect", json.dumps({ #lets the user know what is up
        "userID" : AccId,
        "reason" : "Your account has been wiped! F"
    }))
    if UserConfig["HasRelax"]:
        mycursor.execute("DELETE FROM scores_relax WHERE userid = %s", (AccId,))
    if UserConfig["HasAutopilot"]:
        mycursor.execute("DELETE FROM scores_ap WHERE userid = %s", (AccId,))
    WipeVanilla(AccId)
    if UserConfig["HasRelax"]:
        WipeRelax(AccId)
    if UserConfig["HasAutopilot"]:
        WipeAutopilot(AccId)

def WipeVanilla(AccId):
    """Wiped vanilla scores for user."""
    mycursor.execute("""UPDATE
            users_stats
        SET
            ranked_score_std = 0,
            playcount_std = 0,
            total_score_std = 0,
            replays_watched_std = 0,
            ranked_score_taiko = 0,
            playcount_taiko = 0,
            total_score_taiko = 0,
            replays_watched_taiko = 0,
            ranked_score_ctb = 0,
            playcount_ctb = 0,
            total_score_ctb = 0,
            replays_watched_ctb = 0,
            ranked_score_mania = 0,
            playcount_mania = 0,
            total_score_mania = 0,
            replays_watched_mania = 0,
            total_hits_std = 0,
            total_hits_taiko = 0,
            total_hits_ctb = 0,
            total_hits_mania = 0,
            unrestricted_pp = 0,
            level_std = 0,
            level_taiko = 0,
            level_ctb = 0,
            level_mania = 0,
            playtime_std = 0,
            playtime_taiko = 0,
            playtime_ctb = 0,
            playtime_mania = 0,
            avg_accuracy_std = 0.000000000000,
            avg_accuracy_taiko = 0.000000000000,
            avg_accuracy_ctb = 0.000000000000,
            avg_accuracy_mania = 0.000000000000,
            pp_std = 0,
            pp_taiko = 0,
            pp_ctb = 0,
            pp_mania = 0
        WHERE
            id = %s
    """, (AccId,))
    mycursor.execute("DELETE FROM scores WHERE userid = %s", (AccId,))
    mycursor.execute("DELETE FROM users_beatmap_playcount WHERE user_id = %s", (AccId,))
    mydb.commit()

def WipeRelax(AccId):
    """Wipes the relax user data."""
    mycursor.execute("""UPDATE
            rx_stats
        SET
            ranked_score_std = 0,
            playcount_std = 0,
            total_score_std = 0,
            replays_watched_std = 0,
            ranked_score_taiko = 0,
            playcount_taiko = 0,
            total_score_taiko = 0,
            replays_watched_taiko = 0,
            ranked_score_ctb = 0,
            playcount_ctb = 0,
            total_score_ctb = 0,
            replays_watched_ctb = 0,
            ranked_score_mania = 0,
            playcount_mania = 0,
            total_score_mania = 0,
            replays_watched_mania = 0,
            total_hits_std = 0,
            total_hits_taiko = 0,
            total_hits_ctb = 0,
            total_hits_mania = 0,
            unrestricted_pp = 0,
            level_std = 0,
            level_taiko = 0,
            level_ctb = 0,
            level_mania = 0,
            playtime_std = 0,
            playtime_taiko = 0,
            playtime_ctb = 0,
            playtime_mania = 0,
            avg_accuracy_std = 0.000000000000,
            avg_accuracy_taiko = 0.000000000000,
            avg_accuracy_ctb = 0.000000000000,
            avg_accuracy_mania = 0.000000000000,
            pp_std = 0,
            pp_taiko = 0,
            pp_ctb = 0,
            pp_mania = 0
        WHERE
            id = %s
    """, (AccId,))
    mycursor.execute("DELETE FROM scores_relax WHERE userid = %s", (AccId,))
    mycursor.execute("DELETE FROM rx_beatmap_playcount WHERE user_id = %s", (AccId,))
    mydb.commit()

def WipeAutopilot(AccId):
    """Wipes the autopilot user data."""
    mycursor.execute("""UPDATE
            ap_stats
        SET
            ranked_score_std = 0,
            playcount_std = 0,
            total_score_std = 0,
            replays_watched_std = 0,
            ranked_score_taiko = 0,
            playcount_taiko = 0,
            total_score_taiko = 0,
            replays_watched_taiko = 0,
            ranked_score_ctb = 0,
            playcount_ctb = 0,
            total_score_ctb = 0,
            replays_watched_ctb = 0,
            ranked_score_mania = 0,
            playcount_mania = 0,
            total_score_mania = 0,
            replays_watched_mania = 0,
            total_hits_std = 0,
            total_hits_taiko = 0,
            total_hits_ctb = 0,
            total_hits_mania = 0,
            unrestricted_pp = 0,
            level_std = 0,
            level_taiko = 0,
            level_ctb = 0,
            level_mania = 0,
            playtime_std = 0,
            playtime_taiko = 0,
            playtime_ctb = 0,
            playtime_mania = 0,
            avg_accuracy_std = 0.000000000000,
            avg_accuracy_taiko = 0.000000000000,
            avg_accuracy_ctb = 0.000000000000,
            avg_accuracy_mania = 0.000000000000,
            pp_std = 0,
            pp_taiko = 0,
            pp_ctb = 0,
            pp_mania = 0
        WHERE
            id = %s
    """, (AccId,))
    mycursor.execute("DELETE FROM scores_ap WHERE userid = %s", (AccId,))
    mycursor.execute("DELETE FROM ap_beatmap_playcount WHERE user_id = %s", (AccId,))
    mydb.commit()

def ResUnTrict(id : int, note: str = None):
    """Restricts or unrestricts account yeah."""
    mycursor.execute("SELECT privileges FROM users WHERE id = %s", (id,))
    Privilege = mycursor.fetchall()
    if len(Privilege) == 0:
        return
    Privilege = Privilege[0][0]
    if Privilege == 2: #if restricted
        mycursor.execute("UPDATE users SET privileges = 3, ban_datetime = 0 WHERE id = %s LIMIT 1", (id,)) #unrestricts
        TheReturn = False
    else:
        wip = "Your account has been restricted! Check with staff to see whats up."
        params = {"k": UserConfig['FokaKey'], "to": GetUser(id)["Username"], "msg": wip}
        FokaMessage(params)
        TimeBan = round(time.time())
        mycursor.execute("UPDATE users SET privileges = 2, ban_datetime = %s WHERE id = %s", (TimeBan, id,)) #restrict em bois
        RemoveFromLeaderboard(id)
        TheReturn = True

        # We append the note if it exists to the thingy init bruv
        if note:
            mycursor.execute("UPDATE users SET notes = CONCAT(notes, %s) WHERE id = %s LIMIT 1", ("\n" + note, id))

        # First places KILL.
        mycursor.execute(
            "SELECT beatmap_md5 FROM first_places WHERE user_id = %s",
            (id,)
        )
        recalc_maps = mycursor.fetchall()

        # Delete all of their old.
        mycursor.execute("DELETE FROM first_places WHERE user_id = %s", 
            (id,)
        )
        for bmap_md5, in recalc_maps: calc_first_place(bmap_md5)
    UpdateBanStatus(id)
    mydb.commit()
    return TheReturn

def FreezeHandler(id : int):
    mycursor.execute("SELECT frozen FROM users WHERE id = %s", (id,))
    Status = mycursor.fetchall()
    if len(Status) == 0:
        return
    Frozen = Status[0][0]
    if Frozen:
        mycursor.execute("UPDATE users SET frozen = 0, freezedate = 0, firstloginafterfrozen = 1 WHERE id = %s", (id,))
        mycursor.execute(f"SELECT * FROM user_badges WHERE user = {id} AND badge = {UserConfig['VerifiedBadgeID']}")
        bruh = mycursor.fetchall()
        if bruh is None:
            mycursor.execute("INSERT IGNORE INTO user_badges (user, badge) VALUES (%s, %s)", (id, UserConfig["VerifiedBadgeID"])) #award verification badge
        TheReturn = False
    else:
        if UserConfig["TimestampType"] == "ainu":
        # example: 20200716 instead of 478923793298473298432789437289472394379847329847328943829489432789473289
            freezedateunix = int(datetime.datetime.utcfromtimestamp(int(time.time()) + 432000).strftime("%Y%m%d"))
        else:
            freezedate = datetime.datetime.now() + datetime.timedelta(days=5)
            freezedateunix = (freezedate-datetime.datetime(1970,1,1)).total_seconds()
        mycursor.execute("UPDATE users SET frozen = 1, freezedate = %s WHERE id = %s", (freezedateunix, id,))
        TheReturn = True
        wip = f"Your account has been frozen. Please join the {UserConfig['ServerName']} Discord and submit a liveplay to a staff member in order to be unfrozen"
        params = {"k": UserConfig['FokaKey'], "to": GetUser(id)["Username"], "msg": wip}
        FokaMessage(params)
    mydb.commit()
    return TheReturn
   
def BanUser(id : int):
    """User go bye bye!"""
    mycursor.execute("SELECT privileges FROM users WHERE id = %s", (id,))
    Privilege = mycursor.fetchall()
    Timestamp = round(time.time())
    if len(Privilege) == 0:
        return
    Privilege = Privilege[0][0]
    if Privilege == 0: #if already banned
        mycursor.execute("UPDATE users SET privileges = 3, ban_datetime = '0' WHERE id = %s", (id,))
        TheReturn = False
    else:
        mycursor.execute("UPDATE users SET privileges = 0, ban_datetime = %s WHERE id = %s", (Timestamp, id,))
        RemoveFromLeaderboard(id)
        r.publish("peppy:disconnect", json.dumps({ #lets the user know what is up
            "userID" : id,
            "reason" : f"You have been banned from {UserConfig['ServerName']}. You will not be missed."
        }))
        TheReturn = True
    UpdateBanStatus(id)
    mydb.commit()
    return TheReturn

def ClearHWID(id : int):
    """Clears the HWID matches for provided acc."""
    mycursor.execute("DELETE FROM hw_user WHERE userid = %s", (id,))
    mydb.commit()

def DeleteAccount(id : int):
    """Deletes the account provided. Press F to pay respects."""
    r.publish("peppy:disconnect", json.dumps({ #lets the user know what is up
        "userID" : id,
        "reason" : f"You have been deleted from {UserConfig['ServerName']}. Bye!"
    }))
    #NUKE. BIG NUKE.
    mycursor.execute("DELETE FROM scores WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM users WHERE id = %s", (id,))
    mycursor.execute("DELETE FROM 2fa WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM 2fa_telegram WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM 2fa_totp WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM beatmaps_rating WHERE user_id = %s", (id,))
    mycursor.execute("DELETE FROM comments WHERE user_id = %s", (id,))
    mycursor.execute("DELETE FROM discord_roles WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM ip_user WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM profile_backgrounds WHERE uid = %s", (id,)) 
    mycursor.execute("DELETE FROM rank_requests WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM reports WHERE to_uid = %s OR from_uid = %s", (id, id,))
    mycursor.execute("DELETE FROM tokens WHERE user = %s", (id,))
    mycursor.execute("DELETE FROM remember WHERE userid = %s", (id,))
    mycursor.execute("DELETE FROM users_achievements WHERE user_id = %s", (id,))
    mycursor.execute("DELETE FROM users_beatmap_playcount WHERE user_id = %s", (id,))
    mycursor.execute("DELETE FROM users_relationships WHERE user1 = %s OR user2 = %s", (id, id,))
    mycursor.execute("DELETE FROM user_badges WHERE user = %s", (id,))
    mycursor.execute("DELETE FROM user_clans WHERE user = %s", (id,))
    mycursor.execute("DELETE FROM users_stats WHERE id = %s", (id,))
    if UserConfig["HasRelax"]:
        mycursor.execute("DELETE FROM scores_relax WHERE userid = %s", (id,))
        mycursor.execute("DELETE FROM rx_stats WHERE id = %s", (id,))
    if UserConfig["HasAutopilot"]:
        mycursor.execute("DELETE FROM scores_ap WHERE userid = %s", (id,))
        mycursor.execute("DELETE FROM ap_stats WHERE id = %s", (id,))
    mydb.commit()

def BanchoKick(id : int, reason):
    """Kicks the user from Bancho."""
    r.publish("peppy:disconnect", json.dumps({ #lets the user know what is up
        "userID" : id,
        "reason" : reason
    }))

def FindWithIp(Ip):
    """Gets array of users."""
    #fetching user id of person with given ip
    mycursor.execute("SELECT userid, ip FROM ip_user WHERE ip = %s", (Ip,))
    UserTruple = mycursor.fetchall()
    #turning the data into array with ids
    UserArray = []
    for x in UserTruple:
        ListToAdd = [x[0], x[1]] #so ip is present for later use
        UserArray.append(ListToAdd)
    UserDataArray = [] #this will have the dicts
    for User in UserArray:
        if len(User) != 0:
            UserData = GetUser(User[0])
            UserData["Ip"] = User[1]
            UserDataArray.append(UserData)
        #lets take a second here to appreciate my naming scheme
    return UserDataArray

def PlayStyle(Enum : int):
    """Returns array of playstyles."""
    #should be similar to privileges (it is)
    Styles = []
    #Play style enums
    Mouse = 1 << 0
    Tablet = 1 << 1
    Keyboard = 1 << 2
    Touchscreen = 1 << 3
    #Nice ones ripple
    Spoon = 1 << 4
    LeapMotion = 1 << 5
    OculusRift = 1 << 6
    Dick = 1 << 7
    Eggplant = 1 << 8

    #if statement time
    if Enum & Mouse >= 1:
        Styles.append("Mouse")
    if Enum & Tablet >= 1:
        Styles.append("Tablet")
    if Enum & Keyboard >= 1:
        Styles.append("Keyboard")
    if Enum & Touchscreen >= 1:
        Styles.append("Touchscreen")
    if Enum & Spoon >= 1:
        Styles.append("Spoon")
    if Enum & LeapMotion >= 1:
        Styles.append("Leap Motion")
    if Enum & OculusRift >= 1:
        Styles.append("Oculus Rift")
    if Enum & Dick >= 1:
        Styles.append("Dick")
    if Enum & Eggplant >= 1:
        Styles.append("Eggplant")
    
    return Styles

def PlayerCountCollection(loop = True):
    """Designed to be ran as thread. Grabs player count every set interval and puts in array."""
    while loop:
        CurrentCount = int(r.get("ripple:online_users").decode("utf-8"))
        PlayerCount.append(CurrentCount)
        time.sleep(UserConfig["UserCountFetchRate"] * 60)
        #so graph doesnt get too huge
        if len(PlayerCount) >= 100:
            PlayerCount.remove(PlayerCount[-1])
    if not loop:
        CurrentCount = int(r.get("ripple:online_users").decode("utf-8"))
        PlayerCount.append(CurrentCount)

def DashActData():
    """Returns data for dash graphs."""
    Data = {}
    Data["PlayerCount"] = json.dumps(PlayerCount) #string for easier use in js
    
    #getting time intervals
    PrevNum = 0
    IntervalList = []
    for x in PlayerCount:
        IntervalList.append(str(PrevNum) + "m")
        PrevNum += UserConfig["UserCountFetchRate"]

    IntervalList.reverse()
    Data["IntervalList"] = json.dumps(IntervalList)
    return Data

def GiveSupporter(AccountID : int, Duration = 30):
    """Gives the target user supporter.
    Args:
        AccountID (int): The account id of the target user.
        Duration (int): The time (in days) that the supporter rank should last
    """ #messing around with docstrings
    #checking if person already has supporter
    #also i believe there is a way better to do this, i am tired and may rewrite this and lower the query count
    mycursor.execute("SELECT privileges FROM users WHERE id = %s LIMIT 1", (AccountID,))
    CurrentPriv = mycursor.fetchone()[0]
    if CurrentPriv & 4:
        #already has supporter, extending
        mycursor.execute("SELECT donor_expire FROM users WHERE id = %s", (AccountID,))
        ToEnd = mycursor.fetchone()[0]
        ToEnd += 86400 * Duration
        mycursor.execute("UPDATE users SET donor_expire = %s WHERE id=%s", (ToEnd, AccountID,))
        mydb.commit()
    else:
        EndTimestamp = round(time.time()) + (86400 * Duration)
        CurrentPriv += 4 #adding donor perms
        mycursor.execute("UPDATE users SET privileges = %s, donor_expire = %s WHERE id = %s", (CurrentPriv, EndTimestamp, AccountID,))
        #allowing them to set custom badges
        mycursor.execute("UPDATE users_stats SET can_custom_badge = 1 WHERE id = %s LIMIT 1", (AccountID,))
        #now we give them the badge
        mycursor.execute("INSERT INTO user_badges (user, badge) VALUES (%s, %s)", (AccountID, UserConfig["DonorBadgeID"]))
        mydb.commit()

def RemoveSupporter(AccountID: int, session):
    """Removes supporter from the target user."""
    mycursor.execute("SELECT privileges FROM users WHERE id = %s LIMIT 1", (AccountID,))
    CurrentPriv = mycursor.fetchone()[0]
    #checking if they dont have it so privs arent messed up
    if not CurrentPriv & 4:
        return
    CurrentPriv -= 4
    mycursor.execute("UPDATE users SET privileges = %s, donor_expire = 0 WHERE id = %s", (CurrentPriv, AccountID,))
    #remove custom badge perms and hide custom badge
    mycursor.execute("UPDATE users_stats SET can_custom_badge = 0, show_custom_badge = 0 WHERE id = %s LIMIT 1", (AccountID,))
    #removing el donor badge
    mycursor.execute("DELETE FROM user_badges WHERE user = %s AND badge = %s LIMIT 1", (AccountID, UserConfig["DonorBadgeID"]))
    mydb.commit()
    User = GetUser(AccountID)
    RAPLog(session["AccountId"], f"deleted the supporter role for {User['Username']} ({AccountID})")

def GetBadges():
    """Gets all the badges."""
    mycursor.execute("SELECT * FROM badges")
    Data = mycursor.fetchall()
    Badges = []
    for badge in Data:
        Badges.append({
            "Id" : badge[0],
            "Name" : badge[1],
            "Icon" : badge[2]
        })
    return Badges

def DeleteBadge(BadgeId : int):
    """"Delets the badge with the gived id."""
    mycursor.execute("DELETE FROM badges WHERE id = %s", (BadgeId,))
    mycursor.execute("DELETE FROM user_badges WHERE badge = %s", (BadgeId,))
    mydb.commit()

def GetBadge(BadgeID:int):
    """Gets data of given badge."""
    mycursor.execute("SELECT * FROM badges WHERE id = %s LIMIT 1", (BadgeID,))
    BadgeData = mycursor.fetchone()
    return {
        "Id" : BadgeData[0],
        "Name" : BadgeData[1],
        "Icon" : BadgeData[2]
    }

def SaveBadge(form):
    """Saves the edits done to the badge."""
    BadgeID = form["badgeid"]
    BadgeName = form["name"]
    BadgeIcon = form["icon"]
    mycursor.execute("UPDATE badges SET name = %s, icon = %s WHERE id = %s", (BadgeName, BadgeIcon, BadgeID,))
    mydb.commit()

def ParseReplay(replay):
    """Parses replay and returns data in dict."""
    Replay = parse_replay_file(replay)
    return {
        #"GameMode" : Replay.game_mode, #commented until enum sorted out
        "GameVersion" : Replay.game_version,
        "BeatmapHash" : Replay.beatmap_hash,
        "Player" : Replay.player_name,
        "ReplayHash" : Replay.replay_hash,
        "300s" : Replay.number_300s,
        "100s" : Replay.number_100s,
        "50s" : Replay.number_50s,
        "Gekis" : Replay.gekis,
        "Katus" : Replay.katus,
        "Misses" : Replay.misses,
        "Score" : Replay.score,
        "Combo" : Replay.max_combo,
        "IsPC" : Replay.is_perfect_combo,
        "Mods" : Replay.mod_combination,
        "Timestamp" : Replay.timestamp,
        "LifeGraph" : Replay.life_bar_graph,
        "ReplayEvents" : Replay.play_data #useful for recreating the replay
    }

def CreateBadge():
    """Creates empty badge."""
    mycursor.execute("INSERT INTO badges (name, icon) VALUES ('New Badge', '')")
    mydb.commit()
    #checking the ID
    mycursor.execute("SELECT id FROM badges ORDER BY id DESC LIMIT 1")
    return mycursor.fetchone()[0]

def GetPriv(PrivID: int):
    """Gets the priv data from ID."""
    mycursor.execute("SELECT * FROM privileges_groups WHERE id = %s", (PrivID,))
    Priv = mycursor.fetchone()
    return {
        "Id" : Priv[0],
        "Name" : Priv[1],
        "Privileges" : Priv[2],
        "Colour" : Priv[3]
    }

def DelPriv(PrivID: int):
    """Deletes a privilege group."""
    mycursor.execute("DELETE FROM privileges_groups WHERE id = %s", (PrivID,))
    mydb.commit()

def UpdatePriv(Form):
    """Updates the privilege from form."""
    #Get previous privilege number
    mycursor.execute("SELECT privileges FROM privileges_groups WHERE id = %s", (Form['id'],))
    PrevPriv = mycursor.fetchone()[0]
    #Update group
    mycursor.execute("UPDATE privileges_groups SET name = %s, privileges = %s, color = %s WHERE id = %s LIMIT 1", (Form['name'], Form['privilege'], Form['colour'], Form['id']))
    #update privs for users
    TheFormPriv = int(Form['privilege'])
    #if TheFormPriv != 0 and TheFormPriv != 3 and TheFormPriv != 2: #i accidentally modded everyone because of this....
    #    mycursor.execute("UPDATE users SET privileges = REPLACE(privileges, %s, %s)", (PrevPriv, TheFormPriv,))
    mydb.commit()

def GetMostPlayed():
    """Gets the beatmap with the highest playcount."""
    mycursor.execute("SELECT beatmap_id, song_name, beatmapset_id, playcount FROM beatmaps ORDER BY playcount DESC LIMIT 1")
    Beatmap = mycursor.fetchone()
    
    return {
        "BeatmapId" : Beatmap[0],
        #추가
        "BeatmapSetId" : Beatmap[2],
        "SongName" : Beatmap[1],
        "Cover" : f"https://b.redstar.moe/bg/{Beatmap[0]}",
        #"Cover" : f"https://assets.ppy.sh/beatmaps/{Beatmap[2]}/covers/cover.jpg",
        "Playcount" : Beatmap[3]
    }
    

def DotsToList(Dots: str):
    """Converts a comma array (like the one ripple uses for badges) to a Python list."""
    return Dots.split(",")

def ListToDots(List: list):
    """Converts Python list to comma array."""
    Result = ""
    for part in List:
        Result += str(part) + ","
    return Result[:-1]

def GetUserBadges(AccountID: int):
    """Gets badges of a user and returns as list."""
    mycursor.execute("SELECT badge FROM user_badges WHERE user = %s", (AccountID,))
    Badges = []
    SQLBadges = mycursor.fetchall()
    for badge in SQLBadges:
        Badges.append(badge[0])

    ##so we dont run into errors where people have no/less than 6 badges
    #so we dont run into errors where people have no/less than 10 badges
    while len(Badges) < 10:
        Badges.append(0)
    return Badges

def SetUserBadges(AccountID: int, Badges: list):
    """Sets badge list to account."""
    """ Realised flaws with this approach
    CurrentBadges = GetUserBadges(AccountID) # so it knows which badges to keep
    ItemFor = 0
    for Badge in Badges:
        if not Badge == CurrentBadges[ItemFor]: #if its not the same
            mycursor.execute("DELETE FROM user_badges WHERE")
        ItemFor += 1
    """
    #This might not be the best and most efficient way but its all ive come up with in my application of user badges
    mycursor.execute("DELETE FROM user_badges WHERE user = %s", (AccountID,)) #deletes all existing badges
    for Badge in Badges:
        if Badge != 0 and Badge != 1: #so we dont add empty badges
            mycursor.execute("INSERT INTO user_badges (user, badge) VALUES (%s, %s)", (AccountID, Badge,))
    mydb.commit()

def GetLog():
    """Gets the newest x (userconfig page size) entries in the log."""

    with open("realistikpanel.log") as Log:
        Log = json.load(Log)

    Log = Log[-UserConfig["PageSize"]:]
    Log.reverse() #still wondering why it doesnt return the reversed list and instead returns none
    LogNr = 0
    #format the timestamps
    for log in Log:
        log["FormatDate"] = TimestampConverter(log["Timestamp"])
        Log[LogNr] = log
        LogNr += 1
    return Log

def GetBuild():
    """Gets the build number of the current version of RealistikPanel."""
    with open("buildinfo.json") as file:
        BuildInfo = json.load(file)
    return BuildInfo["version"]

def CheckExists():
    """Make sure the file exists"""
    if not os.path.exists("rpusers.json"):
        #if doesnt exist
        with open("rpusers.json", 'w') as json_file:
            json.dump({}, json_file, indent=4)

def UpdateUserStore(Username: str):
    """Updates the user info stored in rpusers.json or creates the file."""
    CheckExists()
    
    #gets current log
    with open("rpusers.json", "r") as Log:
        Store = json.load(Log)
    
    Store[Username] = {
        "Username" : Username,
        "LastLogin" : round(time.time()),
        "LastBuild" : GetBuild()
    }

    with open("rpusers.json", 'w+') as json_file:
        json.dump(Store, json_file, indent=4)

    #Updating cached store
    CachedStore[Username] = {
        "Username" : Username,
        "LastLogin" : round(time.time()),
        "LastBuild" : GetBuild()
    }

def GetUserStore(Username: str):
    """Gets user info from the store."""
    CheckExists()
    
    with open("rpusers.json", "r") as Log:
        Store = json.load(Log)
    
    if Username in list(Store.keys()):
        return Store[Username]
    else:
        return {
            "Username": Username,
            "LastLogin" : round(time.time()),
            "LastBuild" : 0
        }

def GetUserID(Username: str):
    """Gets user id from username."""
    mycursor.execute("SELECT id FROM users WHERE username LIKE %s LIMIT 1", (Username,))
    Data = mycursor.fetchall()
    if len(Data) == 0:
        return 0
    return Data[0][0]

def GetStore():
    """Returns user store as list."""
    CheckExists()
    with open("rpusers.json", "r") as RPUsers:
        Store = json.load(RPUsers)
    
    TheList = []
    for x in list(Store.keys()):
        #timeago - bit of an afterthought so sorry for weird implementation
        Store[x]["Timeago"] = TimeToTimeAgo(Store[x]["LastLogin"])
        #Gets User id
        Store[x]["Id"] = GetUserID(x)
        TheList.append(Store[x])

    return TheList

def SplitListTrue(TheList : list):
    """Splits list into 2 halves."""
    """
    length = len(TheList)
    return [ TheList[i*length // 2: (i+1)*length // 2] 
            for i in range(2) ]
    """
    Cool = 0
    List1 = []
    List2 = []
    for Thing in TheList:
        if Cool == 0:
            List1.append(Thing)
            Cool = 1
        else:
            List2.append(Thing)
            Cool = 0
    return [List1, List2]

def SplitList(TheList: list):
    """Splits list and ensures the 1st list is the longer one"""
    SplitLists = SplitListTrue(TheList)
    List1 = SplitLists[0]
    List2 = SplitLists[1]
    if len(List2) > len(List1):
        LastElement = List2[-1]
        List2.remove(LastElement)
        List1.append(LastElement)
    return [List1, List2]

def TimeToTimeAgo(Timestamp: int):
    """Converts a seconds timestamp to a timeago string."""
    DTObj = datetime.datetime.fromtimestamp(Timestamp)
    CurrentTime = datetime.datetime.now()
    return timeago.format(DTObj, CurrentTime)

def RemoveFromLeaderboard(UserID: int):
    """Removes the user from leaderboards."""
    Modes = ["std", "ctb", "mania", "taiko"]
    for mode in Modes:
        #redis for each mode
        r.zrem(f"ripple:leaderboard:{mode}", UserID)
        if UserConfig["HasRelax"]:
            #removes from relax leaderboards
            r.zrem(f"ripple:leaderboard_relax:{mode}", UserID)
        if UserConfig["HasAutopilot"]:
            r.zrem(f"ripple:leaderboard_ap:{mode}", UserID)

        #removing from country leaderboards
        mycursor.execute("SELECT country FROM users_stats WHERE id = %s LIMIT 1", (UserID,))
        Country = mycursor.fetchone()[0]
        if Country != "XX": #check if the country is not set
            r.zrem(f"ripple:leaderboard:{mode}:{Country}", UserID)
            if UserConfig["HasRelax"]:
                r.zrem(f"ripple:leaderboard_relax:{mode}:{Country}", UserID)
            if UserConfig["HasAutopilot"]:
                r.zrem(f"ripple:leaderboard_ap:{mode}:{Country}", UserID)

def UpdateBanStatus(UserID: int):
    """Updates the ban statuses in bancho."""
    r.publish("peppy:ban", UserID)

def SetBMAPSetStatus(BeatmapSet: int, Staus: int, session):
    """Sets status for all beatmaps in beatmapset."""

    mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = %s", (BeatmapSet,))
    beatmaps = mycursor.fetchall()
    
    isstd_istaiko_isctb_ismania = [0, 0, 0, 0]
    for bid in beatmaps:
        log.debug("BeatmapID = {}".format(bid[0]))
        mycursor.execute("SELECT difficulty_std, difficulty_taiko, difficulty_ctb, difficulty_mania FROM beatmaps WHERE beatmap_id = %s", (bid[0],))
        mode = mycursor.fetchall()

        URL = UserConfig["Webhook-std"]

        isskip = 0
        #모든 모드난이도가 0일때 거르는 코드
        if isskip == 0 and mode[0][0] == 0 and mode[0][1] == 0 and mode[0][2] == 0 and mode[0][3] == 0:
            URL = UserConfig["Webhook-std"]
            log.warning("모든 모드의 난이도가 0임, BeatmapID = {}".format(bid[0]))
            log.warning("DB에서 {} 비트맵 데이터 삭제.".format(bid[0]))
            mycursor.execute("DELETE FROM beatmaps WHERE beatmap_id = %s", (bid[0],))
            mydb.commit()
            isskip = 1
        #std
        if isstd_istaiko_isctb_ismania[0] == 0:
            if isskip == 0 and mode[0][0] != 0:
                log.chat(" {} = STD".format(bid[0]))
                isstd_istaiko_isctb_ismania[0] = 1
                URL = UserConfig["Webhook-std"]
                isskip = 1
        #Taiko
        if isstd_istaiko_isctb_ismania[1] == 0:
            if isskip == 0 and mode[0][0] == 0 and mode[0][1] != 0:
                log.chat(" {} = Taiko".format(bid[0]))
                isstd_istaiko_isctb_ismania[1] = 1
                URL = UserConfig["Webhook-taiko"]
                isskip = 1
        #ctb
        if isstd_istaiko_isctb_ismania[2] == 0:
            if isskip == 0 and mode[0][0] == 0 and mode[0][2] != 0:
                log.chat(" {} = CTB".format(bid[0]))
                isstd_istaiko_isctb_ismania[2] = 1
                URL = UserConfig["Webhook-ctb"]
                isskip = 1
        #Mania
        if isstd_istaiko_isctb_ismania[3] == 0:
            if isskip == 0 and mode[0][0] == 0 and mode[0][3] != 0:
                log.chat(" {} = Mania".format(bid[0]))
                isstd_istaiko_isctb_ismania[3] = 1
                URL = UserConfig["Webhook-mania"]
                isskip = 1
    
    log.info("BeatmapSet, isstd_istaiko_isctb_ismania = {}".format(isstd_istaiko_isctb_ismania))
    
    #URL = UserConfig["Webhook-std"]

    mycursor.execute("UPDATE beatmaps SET ranked = %s, ranked_status_freezed = 1 WHERE beatmapset_id = %s", (Staus, BeatmapSet,))
    mydb.commit()

    #getting status text
    if Staus == 0:
        TitleText = "unranked"
    elif Staus == 2:
        TitleText = "ranked"
    elif Staus == 5:
        TitleText = "loved"
    elif Staus == 3:
        TitleText = "Approved"
    elif Staus == 4:
        TitleText = "Qualified"
    
    mycursor.execute("SELECT song_name, beatmap_id FROM beatmaps WHERE beatmapset_id = %s LIMIT 1", (BeatmapSet,))
    MapData = mycursor.fetchone()
    #Getting bmap name without diff
    BmapName = MapData[0].split("[")[0].rstrip() #¯\_(ツ)_/¯ might work
    #webhook, didnt use webhook function as it was too adapted for single map webhook
    #webhook = DiscordWebhook(url=UserConfig["Webhook"])

    with_mode_text_1 = ""
    with_mode_text_2 = ""
    with_mode_text_3 = ""
    with_mode_text_4 = ""

    #with_mode_text 1 ~ 4 값 세팅
    xx_i = 0
    for xx in isstd_istaiko_isctb_ismania:
        if xx == 1:
            if xx_i == 0:
                with_mode_text_1 = "With Std!!  "
            if xx_i == 1:
                with_mode_text_2 = "With Taiko!!  "
            if xx_i == 2:
                with_mode_text_3 = "With Ctb!!  "
            if xx_i == 3:
                with_mode_text_4 = "With Mania!!  "
        xx_i += 1

    xx_i = 0
    for xx in isstd_istaiko_isctb_ismania:
        if xx == 1:
            if xx_i == 0:
                URL = UserConfig["Webhook-std"]
            if xx_i == 1:
                URL = UserConfig["Webhook-taiko"]
            if xx_i == 2:
                URL = UserConfig["Webhook-ctb"]
            if xx_i == 3:
                URL = UserConfig["Webhook-mania"]

            webhook = DiscordWebhook(url=URL)
            embed = DiscordEmbed(description=f"Status Changed by {session['AccountName']}", color=242424)
            embed.set_author(name=f"{BmapName} was just {TitleText}. \n{with_mode_text_1}{with_mode_text_2}{with_mode_text_3}{with_mode_text_4} (Beatmap_Set)", url=f"https://redstar.moe/b/{MapData[1]}", icon_url=f"https://a.redstar.moe/{session['AccountId']}") #will rank to random diff but yea
            embed.set_footer(text="via RealistikPanel!")
            #embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{BeatmapSet}/covers/cover.jpg")
            embed.set_image(url=f"https://b.redstar.moe/bg/{beatmaps[0][0]}")
            webhook.add_embed(embed)
            print(" * Posting webhook!")
            webhook.execute()

        xx_i += 1


    #Ingame #announce추가
    #ingamemsg = f"[https://{UserConfig['ServerURL']}u/{session['AccountId']} {session['AccountName']}] {TitleText.lower()} the map_set [https://redstar.moe/b/{MapData[1]} {BmapName}]  [osu://dl/{BeatmapSet} osu!direct]"
    ingamemsg = f"[{UserConfig['ServerURL']}u/{session['AccountId']} {session['AccountName']}] {TitleText.lower()} the map_set [https://osu.redstar.moe/s/{BeatmapSet} {BmapName}]  [osu://dl/{BeatmapSet} osu!direct]"
    params = {"k": UserConfig['FokaKey'], "to": "#ranked", "msg": ingamemsg}
    FokaMessage(params)


def FindUserByUsername(User: str, Page):
    """Finds user by their username OR email."""
    #calculating page offsets
    Offset = UserConfig["PageSize"] * (Page - 1)
    #checking if its an email
    Split = User.split("@")
    if len(Split) == 2 and "." in Split[1]: #if its an email, 2nd check makes sure its an email and not someone trying to be A E S T H E T I C
        mycursor.execute("SELECT id, username, privileges, allowed FROM users WHERE email LIKE %s LIMIT %s OFFSET %s", (User, UserConfig["PageSize"], Offset,)) #i will keep the like statement unless it causes issues
    else: #its a username
        User = f"%{User}%" #for sql to treat is as substring
        mycursor.execute("SELECT id, username, privileges, allowed FROM users WHERE username LIKE %s LIMIT %s OFFSET %s", (User, UserConfig["PageSize"], Offset,))
    Users = mycursor.fetchall()
    if len(Users) > 0:
        PrivilegeDict = {}
        AllPrivileges = []
        for person in Users:
            AllPrivileges.append(person[2])
        UniquePrivileges = Unique(AllPrivileges)
        #gets all priv info (copy pasted from get users as it is based on same infestructure)
        for Priv in UniquePrivileges:
            mycursor.execute("SELECT name, color FROM privileges_groups WHERE privileges = %s LIMIT 1", (Priv,))
            info = mycursor.fetchall()
            if len(info) == 0:
                PrivilegeDict[str(Priv)] = {
                    "Name" : f"Unknown ({Priv})",
                    "Privileges" : Priv,
                    "Colour" : "danger"
                }
            else:
                info = info[0]
                PrivilegeDict[str(Priv)] = {}
                PrivilegeDict[str(Priv)]["Name"] = info[0]
                PrivilegeDict[str(Priv)]["Privileges"] = Priv
                PrivilegeDict[str(Priv)]["Colour"] = info[1]
                if PrivilegeDict[str(Priv)]["Colour"] == "default" or PrivilegeDict[str(Priv)]["Colour"] == "":
                    #stisla doesnt have a default button so ill hard-code change it to a warning
                    PrivilegeDict[str(Priv)]["Colour"] = "warning"

        TheUsersDict = []
        for yuser in Users:
            #country query
            mycursor.execute("SELECT country FROM users_stats WHERE id = %s", (yuser[0],))
            Country = mycursor.fetchone()[0]
            Dict = {
                "Id" : yuser[0],
                "Name" : yuser[1],
                "Privilege" : PrivilegeDict[str(yuser[2])],
                "Country" : Country
            }
            if yuser[3] == 1:
                Dict["Allowed"] = True
            else:
                Dict["Allowed"] = False
            TheUsersDict.append(Dict)
        
        return TheUsersDict
    else:
        return []

def UpdateCachedStore(): #not used for now
    """Updates the data in the cached user store."""
    UpToDateStore = GetStore()
    for User in UpToDateStore:
        CachedStore[User["Username"]] = {}
        for Key in list(User.keys()):
            CachedStore[User["Username"]][Key] = User[Key]

def GetCachedStore(Username: str):
    if Username in list(CachedStore.keys()):
        return CachedStore[Username]
    else:
        return {
            "Username": Username,
            "LastLogin" : round(time.time()),
            "LastBuild" : 0
        }

def CreateBcrypt(Password: str):
    """Creates hashed password using the hashing methods of Ripple."""
    MD5Password = hashlib.md5(Password.encode('utf-8')).hexdigest()
    BHashed = bcrypt.hashpw(MD5Password.encode("utf-8"), bcrypt.gensalt(10))
    return BHashed.decode()

def ChangePassword(AccountID: int, NewPassword: str):
    """Changes the password of a user with given AccID """
    BCrypted = CreateBcrypt(NewPassword)
    mycursor.execute("UPDATE users SET password_md5 = %s WHERE id = %s", (BCrypted, AccountID,))
    mydb.commit()
    r.publish("peppy:change_pass", {
        "user_id": AccountID
    })

def ChangePWForm(form, session): #this function may be unnecessary but ehh
    """Handles the change password POST request."""
    ChangePassword(form["accid"], form["newpass"])
    User = GetUser(form["accid"])
    RAPLog(session["AccountId"], f"has changed the password of {User['Username']} ({form['accid']})")

def GiveSupporterForm(form):
    """Handles the give supporter form/POST request."""
    GiveSupporter(form["accid"], int(form["time"]))

def GetRankRequests(Page: int):
    """Gets all the rank requests. This may require some optimisation."""
    Page -= 1
    Offset = UserConfig["PageSize"] * Page #for the page system to work
    mycursor.execute("SELECT id, userid, bid, type, time, blacklisted FROM rank_requests WHERE blacklisted = 0 LIMIT %s OFFSET %s", (UserConfig['PageSize'], Offset,))
    RankRequests = mycursor.fetchall()
    #turning what we have so far into
    TheRequests = []
    UserIDs = [] #used for later fetching the users, so we dont have a repeat of 50 queries
    for Request in RankRequests:
        #getting song info, like 50 individual queries at peak lmao
        TriedSet = False
        TriedBeatmap = False
        if Request[3] == "s":
            mycursor.execute("SELECT song_name, beatmapset_id FROM beatmaps WHERE beatmapset_id = %s LIMIT 1", (Request[2],))
            TriedSet = True
        else:
            mycursor.execute("SELECT song_name, beatmapset_id FROM beatmaps WHERE beatmap_id = %s LIMIT 1", (Request[2],))
            TriedBeatmap = True
        Name = mycursor.fetchall()
        #in case it was added incorrectly for some reason?
        if len(Name) == 0:
            if TriedBeatmap:
                mycursor.execute("SELECT song_name, beatmapset_id FROM beatmaps WHERE beatmapset_id = %s LIMIT 1", (Request[2],))
            if TriedSet:
                mycursor.execute("SELECT song_name, beatmapset_id FROM beatmaps WHERE beatmap_id = %s LIMIT 1", (Request[2],))
            Name = mycursor.fetchall()

        #if the info is bad
        if len(Name) == 0:
            SongName = "Darude - Sandstorm (Song not found)"
            BeatmapSetID = 0
            Cover = "https://i.ytimg.com/vi/erb4n8PW2qw/maxresdefault.jpg"
        else:
            SongName = Name[0][0]
            if Request[3] == "s":
                SongName = SongName.split("[")[0] #kind of a way to get rid of diff name
            BeatmapSetID = Name[0][1]
            #Cover
            if TriedBeatmap:
                Cover = f"https://b.redstar.moe/bg/{Request[2]}"
            if TriedSet:
                mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = %s LIMIT 1", (Request[2],))
                bbid = mycursor.fetchone()[0]
                Cover = f"https://b.redstar.moe/bg/{bbid}"

            #Cover = f"https://assets.ppy.sh/beatmaps/{BeatmapSetID}/covers/cover.jpg"
        #nice dict
        TheRequests.append({
            "RequestID" : Request[0],
            "RequestBy" : Request[1],
            "RequestSongID" : Request[2], #not specifically song id or set id
            "Type" : Request[3], #s = set b = single diff
            "Time" : Request[4],
            "TimeFormatted" : TimestampConverter(Request[4], 2),
            "SongName" : SongName,
            "Cover" : Cover,
            "BeatmapSetID" : BeatmapSetID
        })

        if Request[1] not in UserIDs:
            UserIDs.append(Request[1])
    #getting the Requester usernames
    Usernames = {}
    for AccoundIdentity in UserIDs:
        mycursor.execute("SELECT username FROM users WHERE id = %s", (AccoundIdentity,))
        TheID = mycursor.fetchall()
        if len(TheID) == 0:
            Usernames[str(AccoundIdentity)] = {"Username" : f"Unknown! ({AccoundIdentity})"}
        else:
            Usernames[str(AccoundIdentity)] = {"Username" : TheID[0][0]}
    #things arent going to be very performant lmao
    for i in range(0, len(TheRequests)):
        TheRequests[i]["RequestUsername"] = Usernames[str(TheRequests[i]["RequestBy"])]["Username"]
    #flip so it shows newest first yes
    TheRequests.reverse()
    TheRequests = SplitList(TheRequests)
    return TheRequests

def DeleteBmapReq(Req):
    """Deletes the beatmap request."""
    mycursor.execute("DELETE FROM rank_requests WHERE id = %s LIMIT 1", (Req,))
    mydb.commit()

def UserPageCount():
    """Gets the amount of pages for users."""
    #i made it separate, fite me
    mycursor.execute("SELECT count(*) FROM users")
    TheNumber = mycursor.fetchone()[0]
    #working with page number (this is a mess...)
    TheNumber /= UserConfig["PageSize"]
    #if not single digit, round up
    if len(str(TheNumber)) != 0:
        NewNumber = round(TheNumber)
        #if number was rounded down
        if NewNumber == round(int(str(TheNumber).split(".")[0])):
            NewNumber += 1
        TheNumber = NewNumber
    #makign page dict
    Pages = []
    while TheNumber != 0:
        Pages.append(TheNumber)
        TheNumber -= 1
    Pages.reverse()
    return Pages

def RapLogCount():
    """Gets the amount of pages for rap logs."""
    #i made it separate, fite me
    mycursor.execute("SELECT count(*) FROM rap_logs")
    TheNumber = mycursor.fetchone()[0]
    #working with page number (this is a mess...)
    TheNumber /= UserConfig["PageSize"]
    #if not single digit, round up
    if len(str(TheNumber)) != 0:
        NewNumber = round(TheNumber)
        #if number was rounded down
        if NewNumber == round(int(str(TheNumber).split(".")[0])):
            NewNumber += 1
        TheNumber = NewNumber
    #makign page dict
    Pages = []
    while TheNumber != 0:
        Pages.append(TheNumber)
        TheNumber -= 1
    Pages.reverse()
    return Pages

def GetClans(Page: int = 1):
    """Gets a list of all clans (v1)."""
    #offsets and limits
    Page = int(Page) - 1
    Offset = UserConfig["PageSize"] * Page
    #the sql part
    mycursor.execute("SELECT id, name, description, icon, tag FROM clans LIMIT %s OFFSET %s", (UserConfig["PageSize"], Offset))
    ClansDB = mycursor.fetchall()
    #making cool, easy to work with dicts and arrays!
    Clans = []
    for Clan in ClansDB:
        Clans.append({
            "ID" : Clan[0],
            "Name" : Clan[1],
            "Description" : Clan[2],
            "Icon": Clan[3],
            "Tag" : Clan[4]
        })
    return Clans

def GetClanPages():
    """Gets amount of pages for clans."""
    mycursor.execute("SELECT count(*) FROM clans")
    TheNumber = mycursor.fetchone()[0]
    #working with page number (this is a mess...)
    TheNumber /= UserConfig["PageSize"]
    #if not single digit, round up
    if len(str(TheNumber)) != 0:
        NewNumber = round(TheNumber)
        #if number was rounded down
        if NewNumber == round(int(str(TheNumber).split(".")[0])):
            NewNumber += 1
        TheNumber = NewNumber
    #makign page dict
    Pages = []
    while TheNumber != 0:
        Pages.append(TheNumber)
        TheNumber -= 1
    Pages.reverse()
    return Pages

def GetAccuracy(count300, count100, count50, countMiss):
    """Converts 300, 100, 50 and miss count into osu accuracy."""
    try:
        return (50*count50 + 100*count100 + 300*count300) / (3*(countMiss + count50 + count100 + count300))
    except ZeroDivisionError:
        return 0

def GetClanMembers(ClanID: int):
    """Returns a list of clan members."""
    #ok so we assume the list isnt going to be too long
    mycursor.execute("SELECT user FROM user_clans WHERE clan = %s", (ClanID,))
    ClanUsers = mycursor.fetchall()
    if len(ClanUsers) == 0:
        return []
    Conditions = ""
    args = []
    #this is so we can use one long query rather than a bunch of small ones
    for ClanUser in ClanUsers:
        Conditions += f"id = %s OR "
        args.append(ClanUser[0])
    Conditions = Conditions[:-4] #remove the OR
    
    #getting the users
    mycursor.execute(f"SELECT username, id, register_datetime FROM users WHERE {Conditions}", args) #here i use format as the conditions are a trusted input
    UserData = mycursor.fetchall()
    #turning the data into a dictionary list
    ReturnList = []
    for User in UserData:
        ReturnList.append({
            "AccountID" : User[1],
            "Username" : User[0],
            "RegisterTimestamp" : User[2],
            "RegisterAgo" : TimeToTimeAgo(User[2])
        })
    return ReturnList

def GetClan(ClanID: int):
    """Gets information for a specified clan."""
    mycursor.execute("SELECT id, name, description, icon, tag, mlimit FROM clans WHERE id = %s LIMIT 1", (ClanID,))
    Clan = mycursor.fetchone()
    if Clan == None:
        return False
    #getting current member count
    mycursor.execute("SELECT COUNT(*) FROM user_clans WHERE clan = %s", (ClanID,))
    MemberCount = mycursor.fetchone()[0]
    return {
        "ID" : Clan[0],
        "Name" : Clan[1],
        "Description" : Clan[2],
        "Icon" : Clan[3],
        "Tag" : Clan[4],
        "MemberLimit" : Clan[5],
        "MemberCount" : MemberCount
    }

def GetClanOwner(ClanID: int):
    """Gets user info for the owner of a clan."""
    #wouldve been done quicker but i decided to play jawbreaker and only got up to 81%
    mycursor.execute("SELECT user FROM user_clans WHERE clan = %s and perms = 8", (ClanID,))
    AccountID = mycursor.fetchone()[0] #assuming there is an owner and clan exists
    #getting account info
    mycursor.execute("SELECT username FROM users WHERE id = %s", (AccountID,)) #will add more info maybe
    #assuming user exists
    User = mycursor.fetchone()
    return {
        "AccountID" : AccountID,
        "Username" : User[0]
    }

def ApplyClanEdit(Form, session):
    """Uses the post request to set new clan settings."""
    ClanID = Form["id"]
    ClanName = Form["name"]
    ClanDesc = Form["desc"]
    ClanTag = Form["tag"]
    ClanIcon = Form["icon"]
    MemberLimit = Form["limit"]
    mycursor.execute("UPDATE clans SET name=%s, description=%s, tag=%s, mlimit=%s, icon=%s WHERE id = %s LIMIT 1", (ClanName, ClanDesc, ClanTag, MemberLimit, ClanIcon, ClanID))
    mydb.commit()
    # Make all tags refresh.
    mycursor.execute("SELECT user FROM user_clans WHERE clan=%s", (ClanID,))
    for user_id, in mycursor.fetchall(): cache_clan(user_id)
    RAPLog(session["AccountId"], f"edited the clan {ClanName} ({ClanID})")

def NukeClan(ClanID: int, session):
    """Deletes a clan from the face of the earth."""
    Clan = GetClan(ClanID)
    if not Clan:
        return
    
    # Make all tags refresh.
    mycursor.execute("SELECT user FROM user_clans WHERE clan=%s", (ClanID,))
    c_m_db = mycursor.fetchall()
    
    mycursor.execute("DELETE FROM clans WHERE id = %s LIMIT 1", (ClanID,))
    mycursor.execute("DELETE FROM user_clans WHERE clan=%s", (ClanID,))
    # run this after
    for user_id, in c_m_db: cache_clan(user_id)
    mydb.commit()
    RAPLog(session["AccountId"], f"deleted the clan {Clan['Name']} ({ClanID})")

def KickFromClan(AccountID):
    """Kicks user from all clans (supposed to be only one)."""
    mycursor.execute("DELETE FROM user_clans WHERE user = %s", (AccountID,))
    mydb.commit()
    cache_clan(AccountID)

def GetUsersRegisteredBetween(Offset:int = 0, Ahead:int = 24):
    """Gets how many players registered during a given time period (variables are in hours)."""
    #convert the hours to secconds
    Offset *= 3600
    Ahead *= 3600

    CurrentTime = round(time.time())
    #now we get the time - offset
    OffsetTime = CurrentTime - Offset
    AheadTime = OffsetTime - Ahead

    mycursor.execute("SELECT COUNT(*) FROM users WHERE register_datetime > %s AND register_datetime < %s", (AheadTime, OffsetTime))
    Count = mycursor.fetchone()
    if Count == None:
        return 0
    return Count[0]

def GetUsersActiveBetween(Offset:int = 0, Ahead:int = 24):
    """Gets how many players were active during a given time period (variables are in hours)."""
    #yeah this is a reuse of the last function.
    #convert the hours to secconds
    Offset *= 3600
    Ahead *= 3600

    CurrentTime = round(time.time())
    #now we get the time - offset
    OffsetTime = CurrentTime - Offset
    AheadTime = OffsetTime - Ahead

    mycursor.execute("SELECT COUNT(*) FROM users WHERE latest_activity > %s AND latest_activity < %s", (AheadTime, OffsetTime))
    Count = mycursor.fetchone()
    if Count == None:
        return 0
    return Count[0]

def RippleSafeUsername(Username):
    """Generates a ripple-style safe username."""
    return Username.lower().replace(" ", "_").rstrip()

def GetSuggestedRank():
    """Gets suggested maps to rank (based on play count)."""
    mycursor.execute("SELECT beatmap_id, song_name, beatmapset_id, playcount FROM beatmaps WHERE ranked = 0 ORDER BY playcount DESC LIMIT 8")
    Beatmaps = mycursor.fetchall()
    BeatmapList = []
    for TopBeatmap in Beatmaps:
        BeatmapList.append({
            "BeatmapId" : TopBeatmap[0],
            #추가
            "BeatmapSetId" : TopBeatmap[2],
            "SongName" : TopBeatmap[1],
            "Cover" : f"https://b.redstar.moe/bg/{TopBeatmap[0]}",
            #"Cover" : f"https://assets.ppy.sh/beatmaps/{TopBeatmap[2]}/covers/cover.jpg",
            "Playcount" : TopBeatmap[3]
        })
        
    return BeatmapList

def CountRestricted():
    """Calculates the amount of restricted or banned users."""
    mycursor.execute("SELECT COUNT(*) FROM users WHERE privileges = 2")
    Count = mycursor.fetchone()
    if Count == None:
        return 0
    return Count[0]

def GetStatistics(MinPP = 0):
    """Gets statistics for the stats page and is incredibly slow...."""
    #this is going to be a wild one
    # TODO: REWRITE or look into caching this
    MinPP = int(MinPP)
    Days = 7
    RegisterList = []
    DateList = []
    while Days != -1:
        DateList.append(f"{Days+1}d")
        RegisterList.append(GetUsersRegisteredBetween(24*Days))
        Days -= 1
    UsersActiveToday = GetUsersActiveBetween()
    RecentPlay = RecentPlays(TotalPlays = 1000, MinPP=MinPP) #this MIGHT kill performance
    ResctictedCount = CountRestricted()

    return {
        "RegisterGraph" : {
            "RegisterList" : RegisterList,
            "DateList" : DateList
        },
        "ActiveToday" : UsersActiveToday,
        "RecentPlays": RecentPlay,
        "DisallowedCount" : ResctictedCount
    }

def CreatePrivilege():
    """Creates a new default privilege."""
    mycursor.execute("INSERT INTO privileges_groups (name, privileges, color) VALUES ('New Privilege', 0, '')")
    mydb.commit()
    #checking the ID
    mycursor.execute("SELECT id FROM privileges_groups ORDER BY id DESC LIMIT 1")
    return mycursor.fetchone()[0]

def CoolerInt(ToInt):
    """Makes a number an int butt also works with special cases etc if ToInt is None, it returns a 0! Magic."""
    if ToInt == None:
        return 0
    return int(ToInt)

def calc_first_place(beatmap_md5: str, rx: int = 0, mode: int = 0) -> None:
    """Calculates the new first place for a beatmap and inserts it into the
    datbaase.
    
    Args:
        beatmap_md5 (str): The MD5 of the beatmap to set the first place for.
        rx (int): THe custom mode to recalc for (0=vn, 1=rx, 2=ap)
        mode (int): The gamemode to recalc for.
    """

    # We have to work out table.
    table = {
        0: "scores",
        1: "scores_relax",
        2: "scores_ap"
    }.get(rx)

    # WHY IS THE ROSU IMPLEMENTATION SO SCUFFED.
    # FROM scores_ap LEFT JOIN users ON users.id = scores_ap.userid
    mycursor.execute(
        "SELECT s.id, s.userid, s.score, s.max_combo, s.full_combo, s.mods, s.300_count,"
        "s.100_count, s.50_count, s.misses_count, s.time, s.play_mode, s.completed,"
        f"s.accuracy, s.pp, s.playtime, s.beatmap_md5 FROM {table} s RIGHT JOIN users a ON a.id = s.userid WHERE "
        "s.beatmap_md5 = %s AND s.play_mode = %s AND completed = 3 AND a.privileges & 2 ORDER BY pp "
        "DESC LIMIT 1",
        (beatmap_md5, mode)
    )

    first_place_db = mycursor.fetchone()

    # No scores at all.
    if not first_place_db: return

    # INSERT BRRRR
    mycursor.execute(
        """
        INSERT INTO first_places
         (
            score_id,
            user_id,
            score,
            max_combo,
            full_combo,
            mods,
            300_count,
            100_count,
            50_count,
            miss_count,
            timestamp,
            mode,
            completed,
            accuracy,
            pp,
            play_time,
            beatmap_md5,
            relax
         ) VALUES
         (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (*first_place_db, rx)
    )
    mydb.commit()

def cache_clan(user_id: int) -> None:
    """Updates LETS' cached clan tag for a specific user. This is a
    requirement for RealistikOsu lets, or else clan tags may get out of sync.
    """

    r.publish("rosu:clan_update", str(user_id))

def mailSend(session, sender_email, sender_password, to_email, msg, type=""):
    sc = 200
    # SMTP 서버에 연결 및 이메일 전송
    try:
        smtp = smtplib.SMTP_SSL("smtp.daum.net", 465)
        smtp.login(sender_email, sender_password)
        smtp.sendmail(sender_email, to_email, msg.as_string())
        smtp.quit()
        log.info(f"{type} 이메일 전송 성공")
    except Exception as e:
        log.error(f"{type} 이메일 전송 실패:", str(e))
        sc = 503

    # 보낸메일함에 복사
    try:
        imap = imaplib.IMAP4_SSL("imap.daum.net", 993)
        imap.login(sender_email, sender_password)
        imap.append("Sent", None, None, msg.as_bytes())
        log.info("보낸메일함 복사 성공!")
    except Exception as e:
        log.error("보낸메일함 복사 실패:", str(e))
        sc = 500

    # 디코 웹훅 전송
    try:
        if not session["LoggedIn"] or session["AccountId"] == 0 or session["AccountName"] == "" or session["Privilege"] == 0:
            session["AccountId"] = 999
            session["AccountName"] = "Devlant"

        webhook = DiscordWebhook(url=UserConfig["AdminLogWebhook"])
        embed = DiscordEmbed(description=msg.as_string(), color=242424)
        embed.set_author(name=f"{session['AccountName']} Sent {type} email", url=f"{UserConfig['ServerURL']}u/{session['AccountId']}", icon_url=f"{UserConfig['AvatarServer']}999")
        embed.set_footer(text="via RealistikPanel!")
        webhook.add_embed(embed)
        webhook.execute()
        print(" * Posting webhook!")
    except Exception as e:
        log.error(f"디코 웹훅 전송 실패! | {e}")
    return sc

def sendPwresetMail(session, userID, to_email):
    mycursor.execute(f"SELECT username FROM users WHERE id = {userID}")
    username = mycursor.fetchone()[0]

    key = "" 
    for i in range(16) :
        key += random.choice(string.ascii_letters + string.digits) # 랜덤한 문자열 하나 선택

    mycursor.execute(f"INSERT INTO password_recovery (id, k, u, t) VALUES (NULL, 'Realistik Panel : {key}', '{username}', NULL)")
    mydb.commit()

    # 보내는 사람 이메일 계정 정보
    sender_email = UserConfig['Email']
    sender_password = UserConfig['EmailPassword']

    # 이메일 메시지 설정
    subject = f"{username}'s password Recovery KEY"
    body = key

    msg = MIMEMultipart()
    msg['From'] = f'RedstarOSU! Bot Devlant <{sender_email}>'  # 별명을 추가한 부분
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    mailSend(session, sender_email, sender_password, to_email, msg, type="Pwreset")

    return key

def emailBody(country, username, beatmapInfo):
    #765 MILLION ALLSTARS - UNION!! [We are all MILLION!!] +TD(NV), HD, HR, DT, RX (100.0%)
    if country == "KR" or country == "KP":
        body = f"""
<html lang="kr">
    <body style="background-color: rgb(255,255,255);">
    <div style="font-size: 15px;color: rgb(47,41,54);padding: 0;font-family: Helvetica Neue,Helvetica, sans-serif;width: 100%;font-weight: 400;margin: 0;background-color: rgb(255,255,255); background: #ffffff;">
    <div style="padding: 0;font-size: 0;display: none;max-height: 0;font-weight: 400;line-height: 0;"></div>
    <table style="border-radius: 4px;font-size: 15px;color: rgb(47,41,54);border-collapse: separate;border-spacing: 0;max-width: 700px;font-family: Helvetica Neue, helvetica, sans-serif;border: 1.0px solid rgb(199,208,212);padding: 0;width: 100%;font-weight: 400;margin: 15.0px auto;background-color: pink;">
      <tr style="font-weight: 400;">
        <td style="padding: 0;font-weight: 400;margin: 0;text-align: center;">
          <div style="padding: 25px 0 25px 0;font-size: 14px;font-weight: 400;border-bottom: 1.0px solid rgb(222,231,235);">
            <div style="padding: 0 20px;max-width: 600px;font-weight: 400;margin: 0 auto;text-align: left;">
    
                <table style="width: 100%;font-weight: 400;margin-bottom: 0;border-collapse: collapse;">
                  <tr style="font-weight: 400;">
                    <td width="125px" style="padding: 0;font-weight: 400;margin: 0;text-align: center;">
    
                        <h1 style="font-size: 38px;color: rgb(0,0,0);letter-spacing: -1px;padding: 0;font-weight: normal;margin: 0;line-height: 42px;">
                          <a href="https://redstar.moe" style="color: rgb(77, 112, 213);font-weight: 500;text-decoration: none;" target="_blank">
                            <img src="https://redstar.moe/static/logos/ainu.png" height="70px" style="font-weight: 400;" />
                          </a>
                        </h1>
    
                    </td><td style="padding: 0;font-weight: 400;margin: 0;text-align: right;">
                      <span id="Dear username" style="font-weight: 600; font-size: 14px; position: relative; top: -2px;">

                        Dear {username}
                        
                      </span>
                      <br/>
                      <span style="font-size: 14px; position: relative; top: 2px;">

                        Your Account's Status is Changed.

                      </span>
                    </td>
                  </tr>
                </table>
            </div>
          </div>
        </td>
      </tr>
      <tr style="font-weight: 400;">
        <td style="padding: 0;font-weight: 400;margin: 0;text-align: center;">
    
          <div style="padding: 0 20px;max-width: 600px;font-weight: 400;margin: 0 auto;text-align: left;">
            <div style="padding: 30.0px 0 20px;font-weight: 400;background-color: pink">
                <h3 id="Hello, username. Thanks for using our service." style="font-size: 22px;font-weight: 500;margin: 0 0 20px;">

                  안녕하세요, {username}. 저희 서비스를 이용해 주셔서 감사합니다.

                </h3>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">

                  유감스럽게도 회원님의 계정에서 일부 악용 활동이 발견되어 회원님의 계정 상태가 
                  <a style="color: red;">
                    금지됨으로
                  </a>
                  변경되었습니다. 다음은 우리 팀이 판단하는 당신의 점수 중 하나입니다:
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 20px;line-height: 29.3333px;">
                    
                  <a id="Reason for sending mail" target="_blank" href="https://redstar.moe/b/{beatmapInfo["bid"]}" style="color: lightslategray; text-decoration: none;">
                      {beatmapInfo["beatmapInfo"]}
                  </a>
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">

                  물론 저희 팀원들도 사람이기 때문에 이 판단이 틀릴 수도 있습니다. 이 결정이 잘못되었다고 생각하거나 이에 대해 궁금한 점이 있으신 경우, 
                  <a style="color: green; text-decoration: none;" target="_blank" href="mailto:support@redstar.moe">
                      support@redstar.moe 
                  </a>
                  에 회신하거나 저희 팀 공식 Discord: 
                  <a style="color: green; text-decoration: none;" target="_blank" href="https://discord.redstar.moe">
                      https://discord.redstar.moe 
                  </a>
                  에 참가하여 커뮤니티 메니저 팀에게 DM을 보내주십시오.
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  언밴요청에는 2가지 옵션이 있습니다: 라이브 플레이 또는 반성 후 사과문 작성
                  라이브 플레이에서는 다음을 포함해야 합니다.
                    <br>
                    - 컴퓨터 재부팅
                    <br>
                    - 시계 (만약 시간을 증명할 방법이 없으면 <a style="color: green; text-decoration: none;" target="_blank" href="https://www.unixtimestamp.com">https://www.unixtimestamp.com</a> 으로 가서 F5를 눌러서 증명하는 방법도 있습니다.)
                    <br>
                    - 핸드캠
                    <br>
                    - 작업 관리자 프로세스를 끝까지 아래로 내린 후 바로 osu!를 실행
                    <br>
                    - 다시 작업 관리자 프로세스를 끝까지 아래로 내림
                    <br>
                    - 계정의 최고 pp 기록 #1 ~ #10 중 최소 2개를 다시 시연하거나 그와 비슷한 pp기록을 세웁니다.
                    <br>
                    ---------------------------------------------------------------
                    <br>
                    두 번째 옵션을 선택하면 반성문은 한 번만 용서됩니다. 이의신청서를 작성하여 언밴되었음에도 불구하고 의심스러운 행위로 인해 계정이 다시 제한되는 경우 도움을 드릴 수 없음을 알려드립니다. 따라서 저장한 기록이 사실이라면 반성문보다는 녹화를 해주시기 바랍니다.
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  <a style="color: red;">
                    경고: 
                  </a>
                  서버 규칙에 따라 서버는 1인당 하나의 계정만 허용합니다. 절대 다른 계정을 만들지 마세요!! 이것은 당신에게 나쁜 영향을 미칠 수 있습니다.
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  <!-- <a style="color: red;">
                    이 메일은 보내기 전용이므로 이 이메일에 답장하지 마세요.
                  </a> -->
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  <a style="color: blue;">
                    안부를 전합니다.
                    <br>
                    레드스타팀.
                  </a>
                
                </p>

            </div>
          </div>
    
          <div style="max-width: 600px;padding: 0 20px; font-weight: 400;margin: 0 auto;text-align: left;">
            <div style="padding: 20px 0 40px 0;border-top: 1px solid rgb(231,235,238);font-weight: 400; text-align: center;">
    
              <a style="cursor: pointer; color: rgb(104,114,118); font-weight: 500;text-decoration: none;">
              
                  RedstarOSU!

              </a>

              <p>
                이 이메일은 python을 통해 자동으로 보내진 이메일 입니다.
              </p>
    
              <p>
                당신의 국가가 KR 또는 KP 이므로 한국어로 이메일이 전송되었습니다. 당신의 국가:{country}
              </p>
    
            </div>
          </div>
        </td>
      </tr>
    </table>
    </div>

    </body>
</html>
"""
    else:
        body = f"""
<html lang="en">
    <body style="background-color: rgb(255,255,255);">
    <div style="font-size: 15px;color: rgb(47,41,54);padding: 0;font-family: Helvetica Neue,Helvetica, sans-serif;width: 100%;font-weight: 400;margin: 0;background-color: rgb(255,255,255); background: #ffffff;">
    <div style="padding: 0;font-size: 0;display: none;max-height: 0;font-weight: 400;line-height: 0;"></div>
    <table style="border-radius: 4px;font-size: 15px;color: rgb(47,41,54);border-collapse: separate;border-spacing: 0;max-width: 700px;font-family: Helvetica Neue, helvetica, sans-serif;border: 1.0px solid rgb(199,208,212);padding: 0;width: 100%;font-weight: 400;margin: 15.0px auto;background-color: pink;">
      <tr style="font-weight: 400;">
        <td style="padding: 0;font-weight: 400;margin: 0;text-align: center;">
          <div style="padding: 25px 0 25px 0;font-size: 14px;font-weight: 400;border-bottom: 1.0px solid rgb(222,231,235);">
            <div style="padding: 0 20px;max-width: 600px;font-weight: 400;margin: 0 auto;text-align: left;">
    
                <table style="width: 100%;font-weight: 400;margin-bottom: 0;border-collapse: collapse;">
                  <tr style="font-weight: 400;">
                    <td width="125px" style="padding: 0;font-weight: 400;margin: 0;text-align: center;">
    
                        <h1 style="font-size: 38px;color: rgb(0,0,0);letter-spacing: -1px;padding: 0;font-weight: normal;margin: 0;line-height: 42px;">
                          <a href="https://redstar.moe" style="color: rgb(77, 112, 213);font-weight: 500;text-decoration: none;" target="_blank">
                            <img src="https://redstar.moe/static/logos/ainu.png" height="70px" style="font-weight: 400;" />
                          </a>
                        </h1>
    
                    </td><td style="padding: 0;font-weight: 400;margin: 0;text-align: right;">
                      <span id="Dear username" style="font-weight: 600; font-size: 14px; position: relative; top: -2px;">

                        Dear {username}
                        
                      </span>
                      <br/>
                      <span style="font-size: 14px; position: relative; top: 2px;">

                        Your Account's Status is Changed.

                      </span>
                    </td>
                  </tr>
                </table>
            </div>
          </div>
        </td>
      </tr>
      <tr style="font-weight: 400;">
        <td style="padding: 0;font-weight: 400;margin: 0;text-align: center;">
    
          <div style="padding: 0 20px;max-width: 600px;font-weight: 400;margin: 0 auto;text-align: left;">
            <div style="padding: 30.0px 0 20px;font-weight: 400;background-color: pink">
                <h3 id="Hello, username. Thanks for using our service." style="font-size: 22px;font-weight: 500;margin: 0 0 20px;">

                  Hello, {username}. Thanks for using our service.

                </h3>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">

                  Unfortunately, our team caught some exploitative activities in your account. So, your account's status is changed to
                  <a style="color: red;">
                      Banned.
                  </a>
                  here is one of your score that our team judgement:
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 20px;line-height: 29.3333px;">
                    
                  <a id="Reason for sending mail" target="_blank" href="https://redstar.moe/b/{beatmapInfo["bid"]}" style="color: lightslategray; text-decoration: none;">
                      {beatmapInfo["beatmapInfo"]}
                  </a>
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">

                  Of course, our team members are also human, so this judgement may be wrong.If you think this decision is wrong or have a question about this, please reply to 
                  <a style="color: green; text-decoration: none;" target="_blank" href="mailto:support@redstar.moe">
                      support@redstar.moe
                  </a>
                  or join our official discord: 
                  <a style="color: green; text-decoration: none;" target="_blank" href="https://discord.redstar.moe">
                      https://discord.redstar.moe
                  </a>
                  and DM to our Team members.
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  If you reply to the appeal, you have 2 options: liveplay or appeal after self-reflection.
                  In liveplay, you must include must be included :
                  <br>
                  - Reboot your computer
                  <br>
                  - Clock (If there is no way to prove the time, go to <a style="color: green; text-decoration: none;" target="_blank" href="https://www.unixtimestamp.com">https://www.unixtimestamp.com</a> You can also go ahead and press F5 to prove it.)
                  <br>
                  - handcam
                  <br>
                  - scrolling the Task Manager processes, and run osu! immediately
                  <br>
                  - scrolling the Task Manager processes Again
                  <br>
                  - Re-demonstrate at least two of the account's best performance pp records 1 to 10 or equivalent.
                  <br>
                  ---------------------------------------------------------------
                  <br>
                  if you select the second option, an appeal is forgiven only once. We would like to inform you that we cannot help you if your account is restricted due to suspicious behavior even though the restriction has been lifted by writing an appeal. Therefore, if the record you saved is true, please record the liveplay rather than writing an appeal.
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  <a style="color: red;">
                      WARNING: 
                  </a>
                  According to our server rules, our server allows only one account per person. Never create another account!! This can have a bad effect on you.
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  <!-- <a style="color: red;">
                      This mail is SEND-ONLY, so DON'T reply to this email.
                  </a> -->
                
                </p>
                <p style="font-weight: 400;margin: 0 0 20px;font-size: 15px;line-height: 22px;">
                    
                  <a style="color: blue;">
                      Best Regards.
                      <br>
                      Redstar Team.
                  </a>
                
                </p>

            </div>
          </div>
    
          <div style="max-width: 600px;padding: 0 20px; font-weight: 400;margin: 0 auto;text-align: left;">
            <div style="padding: 20px 0 40px 0;border-top: 1px solid rgb(231,235,238);font-weight: 400; text-align: center;">
    
              <a style="cursor: pointer; color: rgb(104,114,118); font-weight: 500;text-decoration: none;">
              
                  RedstarOSU!

              </a>

              <p>
                This email is automatically sent through python.
              </p>
    
              <p>
                The email was sent in English because your country is not KR or KP. Your country:{country}
              </p>
    
            </div>
          </div>
        </td>
      </tr>
    </table>
    </div>

    </body>
</html>
"""
    return body

def sendAutoBanMail(session, AuthKey, userID, to_email, beatmapInfo):
    mycursor.execute(f"SELECT users.username AS username, users_stats.country AS country FROM users JOIN users_stats ON users.id = users_stats.id WHERE users.id = {userID}")
    result = mycursor.fetchone()
    username = result[0]
    country = result[1].upper()

    # 보내는 사람 이메일 계정 정보
    sender_email = UserConfig['Email']
    sender_password = UserConfig['EmailPassword']

    # 이메일 메시지 설정
    subject = f"{username}, Your Account's Status is Changed"
    body = emailBody(country, username, beatmapInfo)

    msg = MIMEMultipart()
    msg['From'] = f'RedstarOSU! Bot Devlant <{sender_email}>'  # 별명을 추가한 부분
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    #DashData()
    try:
        AuthKeyCheck = r.get(f"RealistikPanel:AutoBanMailAuthKey:{userID}").decode("utf-8")
    except:
        return 404

    if AuthKey == AuthKeyCheck:
        r.delete(f"RealistikPanel:AutoBanMailAuthKey:{userID}")
    else:
        return 403

    return mailSend(session, sender_email, sender_password, to_email, msg, type="AutoBan")

def sendBanMail(session, userID, to_email, beatmapInfo):
    mycursor.execute(f"SELECT users.username AS username, users_stats.country AS country FROM users JOIN users_stats ON users.id = users_stats.id WHERE users.id = {userID}")
    result = mycursor.fetchone()
    username = result[0]
    country = result[1].upper()

    # 보내는 사람 이메일 계정 정보
    sender_email = UserConfig['Email']
    sender_password = UserConfig['EmailPassword']

    # 이메일 메시지 설정
    subject = f"{username}, Your Account's Status is Banned"
    body = emailBody(country, username, beatmapInfo)

    msg = MIMEMultipart()
    msg['From'] = f'RedstarOSU! Team {session["AccountName"]} <{sender_email}>'  # 별명을 추가한 부분
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    return mailSend(session, sender_email, sender_password, to_email, msg, type="Ban")

def sendEmail(session, to_email, subject, msg):
    # 보내는 사람 이메일 계정 정보
    sender_email = UserConfig['Email']
    sender_password = UserConfig['EmailPassword']

    # 이메일 메시지 설정
    subject = subject
    body = msg

    msg = MIMEMultipart()
    msg['From'] = f'RedstarOSU! Team {session["AccountName"]} <{sender_email}>'  # 별명을 추가한 부분
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    return mailSend(session, sender_email, sender_password, to_email, msg, type="")