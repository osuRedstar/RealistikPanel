#This file is responsible for running the web server and (mostly nothing else)
from flask import Flask, render_template, session, redirect, url_for, request, send_file, jsonify, Response
from werkzeug.middleware.proxy_fix import ProxyFix
from defaults import *
from config import UserConfig
from functions import *
from colorama import Fore, init
import os
from updater import *
from threading import Thread
import logging
import requests

#log함수? 추가
from lets_common_log import logUtils as log

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

print(f" {Fore.BLUE}Running Build {GetBuild()}")
ConsoleLog(f"RealistikPanel (Build {GetBuild()}) started!")

app = Flask(__name__)
app.secret_key = os.urandom(24) #encrypts the session cookie
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2 if UserConfig["UseCloudFlareProxy"] else 1, x_proto=1, x_host=1, x_port=1, x_prefix=1) #ProxyFix 미들웨어 추가

class NoPingFilter(logging.Filter):
    def filter(self, record):
        return "/ping" not in record.getMessage()
# Apply the filter to Flask's default logger
logging.getLogger('werkzeug').addFilter(NoPingFilter())

ServerDomain = UserConfig["ServerURL"].replace("https://", "").replace("/", "")
requestHeaders = {"User-Agent": UserConfig["GitHubRepo"], "Referer": UserConfig["ServerURL"].replace("://", "://admin.")}

@app.route("/")
def home():
    if session["LoggedIn"]: return redirect(url_for("dash"))
    else: return redirect(url_for("login"))

@app.route("/dash/")
def dash():
    if HasPrivilege(session["AccountId"]):
        #responsible for the "HeY cHeCk OuT tHe ChAnGeLoG"
        User = GetCachedStore(session["AccountName"])
        Thread(target=UpdateUserStore, args=(session["AccountName"],)).start()
        if User["LastBuild"] == GetBuild():
            return render_template("dash.html", title="Dashboard", session=session, data=DashData(), restricteduserlist=json.loads(RestrictedUserList(dash=True))[0], banneduserlist=json.loads(BannedUserList(dash=True))[0], plays=RecentPlays(), config=UserConfig, Graph=DashActData(), MostPlayed=GetMostPlayed())
        else:
            return render_template("dash.html", title="Dashboard", session=session, data=DashData(), restricteduserlist=json.loads(RestrictedUserList(dash=True))[0], banneduserlist=json.loads(BannedUserList(dash=True))[0], plays=RecentPlays(), config=UserConfig, Graph=DashActData(), MostPlayed=GetMostPlayed(), info=f"Hey! RealistikPanel has been recently updated to build <b>{GetBuild()}</b>! Check out <a href='/changelogs'>what's new here!</a>")
    else:
        return NoPerm(session, request.url)
    

@app.route("/recent_RegisteredUsers")
def RecentRegisteredUsers():
    if HasPrivilege(session["AccountId"], 6):
        #Nerina
        #mycursor.execute("SELECT users.id, users.osuver, users.username, users.username_safe, users.ban_datetime FROM users WHERE current_status NOT IN ('Offline') ORDER BY %s", [query])
        mycursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 1");
        data = mycursor.fetchall();

        row_headers = [x[0] for x in mycursor.description]
        values = list(data)

        result = []

        for i in values:
            result.append(dict(zip(row_headers, i)))

        
        mycursor.execute("SELECT * FROM users_stats ORDER BY id DESC LIMIT 1");
        data = mycursor.fetchall();

        row_headers = [x[0] for x in mycursor.description]
        values = list(data)

        result2 = []

        for i in values:
            result2.append(dict(zip(row_headers, i)))

        
        mycursor.execute("SELECT * FROM ip_user ORDER BY userid DESC LIMIT 1");
        data = mycursor.fetchall();

        row_headers = [x[0] for x in mycursor.description]
        values = list(data)

        result3 = []

        for i in values:
            result3.append(dict(zip(row_headers, i)))
        
        
        return Response(json.dumps({"users":result, "users_stats":result2, "ip_users":result3}, indent=2, ensure_ascii=False), content_type='application/json')
    else:
        return NoPerm(session, request.url)


@app.route("/onlineusers_list")
def OnlineUserList():
    query = request.args.get("q")
    log.debug("onlinelist query = {}".format(query))
    if query is None:
        log.debug("리다이렉트 댐")
        return redirect(f"https://admin.{ServerDomain}/onlineusers_list?q=id")
    #sql 인젝션 방지 (?)
    elif query != "id" and query != "username" and query != "current_status":
        log.warning("조회 되지 않는 쿼리 입력 : {}".format(query))
        return "조회 되지 않는 쿼리 입력 : {}".format(query)

    #Nerina
    mycursor.execute("SELECT id, username, current_status FROM users_stats WHERE current_status NOT IN ('Offline') ORDER BY %s", [query]);
    data = mycursor.fetchall();

    row_headers = [x[0] for x in mycursor.description]
    values = list(data)

    result = []

    for i in values:
        result.append(dict(zip(row_headers, i)))
    
    return Response(json.dumps([len(data), result], indent=2, ensure_ascii=False), content_type='application/json')

    #return render_template("dash.html", title="Dashboard", session=session, data=DashData(), plays=RecentPlays(), config=UserConfig, Graph=DashActData(), MostPlayed=GetMostPlayed())

@app.route("/restrictedusers_list")
def RestrictedUserList(dash=False):
    #/dash 에러 방지
    if not dash:
        query = request.args.get("q")
        log.debug("restrictedlist query = {}".format(query))
        if query is None:
            log.debug("리다이렉트 댐")
            return redirect(f"https://admin.{ServerDomain}/restrictedusers_list?q=id")
        #sql 인젝션 방지 (?)
        elif query != "id" and query != "username" and query != "ban_datetime" and query != "privileges":
            log.warning("조회 되지 않는 쿼리 입력 : {}".format(query))
            return "조회 되지 않는 쿼리 입력 : {}".format(query)
    else:
        query = "id"
        log.info("/dash에서 /restrictedusers_list 속 함수 요청댐. 에러 방지를 위하여 쿼리 리다이렉트 비활성화 (?)")

    #Nerina
    mycursor.execute("SELECT id, username, ban_datetime, privileges FROM users WHERE ban_datetime NOT IN ('0') and privileges = 2 ORDER BY %s", [query]);
    data = mycursor.fetchall();

    row_headers = [x[0] for x in mycursor.description]
    values = list(data)

    result = []

    for i in values:
        result.append(dict(zip(row_headers, i)))
    
    if dash:
        return json.dumps([len(data), result])
    else:
        return Response(json.dumps([len(data), result], indent=2, ensure_ascii=False), content_type='application/json')

@app.route("/bannedusers_list")
def BannedUserList(dash=False):
    #/dash 에러 방지
    if not dash:
        query = request.args.get("q")
        log.debug(f"bannedlist query = {query}")
        if query is None:
            log.debug("리다이렉트 댐")
            return redirect(f"https://admin.{ServerDomain}/bannedusers_list?q=id")
        #sql 인젝션 방지 (?)
        elif query != "id" and query != "username" and query != "ban_datetime" and query != "privileges":
            log.warning(f"조회 되지 않는 쿼리 입력 : {query}")
            return f"조회 되지 않는 쿼리 입력 : {query}"
    else:
        query = "id"
        log.info("/dash에서 /bannedusers_list 속 함수 요청댐. 에러 방지를 위하여 쿼리 리다이렉트 비활성화 (?)")

    #Nerina
    mycursor.execute("SELECT id, username, ban_datetime, privileges FROM users WHERE ban_datetime NOT IN ('0') and privileges = 0 ORDER BY %s", [query]);
    data = mycursor.fetchall();

    row_headers = [x[0] for x in mycursor.description]
    values = list(data)

    result = []

    for i in values:
        result.append(dict(zip(row_headers, i)))
    
    if dash:
        return json.dumps([len(data), result])
    else:
        return Response(json.dumps([len(data), result], indent=2, ensure_ascii=False), content_type='application/json')

@app.route("/status")
def status():
    query = request.args.get("json")
    log.debug("status query = {}".format(query))
    if query == "1":
        try:
            MediaServer = requests.get(f"https://b.{ServerDomain}/status", headers=requestHeaders, timeout=1).json()
        except Exception as err:
            print(f"[ERROR] https://b.{ServerDomain}/status: ", err)
            MediaServer = {"code" : 503, "oszCount" : -1}
        return Response(json.dumps({"Bancho": BanchoStatus().json, "LETS": LetsStatus().json, "API": ApiStatus().json, "MediaServer": MediaServer}, indent=2, ensure_ascii=False), content_type='application/json')
    return render_template("dash.html", title="Dashboard", session=session, data=DashData(), restricteduserlist=json.loads(RestrictedUserList(dash=True))[0], banneduserlist=json.loads(BannedUserList(dash=True))[0], plays=RecentPlays(), config=UserConfig, Graph=DashActData(), MostPlayed=GetMostPlayed())

@app.route("/login", methods = ["GET", "POST"])
def login():
    redirect_url = request.args.get("redirect_url")
    if redirect_url is None: redirect_url = url_for("home")

    if not session["LoggedIn"] and not HasPrivilege(session["AccountId"]):
        if request.method == "GET":
            return render_template("login.html", conf = UserConfig)
        if request.method == "POST":
            LoginData = LoginHandler(request.form["username"], request.form["password"])
            if not LoginData[0]:
                return render_template("login.html", alert=LoginData[1], conf = UserConfig)
            else:
                SessionToApply = LoginData[2]
                #modifying the session
                for key in list(SessionToApply.keys()):
                    session[key] = SessionToApply[key]
                return redirect(redirect_url)
    else: return redirect(url_for("dash"))

@app.route("/logout")
def logout():
    #modifying the session
    for x in list(ServSession.keys()):
        session[x] = ServSession[x]
    return redirect(url_for("home"))


#Send Foka Message 추가
@app.route("/fokamessage", methods = ["GET", "POST"])
def foka_message():
    if request.method == "GET":
        if HasPrivilege(session["AccountId"], 3):
            return render_template("fokamessage.html", title="Fokamessage", data=DashData(), session=session, config=UserConfig)
        else:
            return NoPerm(session, request.url)
    else:
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
            return NoPerm(session, request.url)
        else:
            fro = request.form.get('from')
            channel = request.form['channel']
            msg = request.form['message']
            FokaMessage({"k": UserConfig['FokaKey'], "fro": fro, "to": channel, "msg": msg}) #Ingame #announce추가
            return render_template("fokamessage.html", title="Fokamessage", data=DashData(), session=session, config=UserConfig, success=f"Successfully Send FokaMessage! \n{msg}")
            #return redirect(f"/fokamessage") #does this even work

@app.route("/iptousers", methods = ["GET", "POST"])
def ipToUser():
    if request.method == "GET":
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
            return NoPerm(session, request.url)
        else:
            return render_template("iptousers.html", title="IP To users", data=DashData(), session=session, config=UserConfig)
    else:
        ip = request.form['IP']
        mycursor.execute("SELECT userid, username FROM ip_user INNER JOIN users ON ip_user.userid = users.id WHERE ip = %s", [ip])
        result = [{"userID": i[0], "username": i[1]} for i in mycursor.fetchall()]
        return Response(json.dumps({"ip": ip, "userinfo": result}, indent=2, ensure_ascii=False), content_type='application/json')
@app.route("/iptousers/<ip>")
def ipToUserApi(ip):
    if not HasPrivilege(session["AccountId"]): #mixing things up eh
        return NoPerm(session, request.url)
    else:
        mycursor.execute("SELECT userid, username FROM ip_user INNER JOIN users ON ip_user.userid = users.id WHERE ip = %s", [ip])
        result = [{"userID": i[0], "username": i[1]} for i in mycursor.fetchall()]
        return Response(json.dumps({"ip": ip, "userinfo": result}, indent=2, ensure_ascii=False), content_type='application/json')

@app.route("/bancho/settings", methods = ["GET", "POST"])
def BanchoSettings():
    if HasPrivilege(session["AccountId"], 4):
        #no bypassing it.
        if request.method == "GET":
            return render_template("banchosettings.html", preset=FetchBSData(), title="Bancho Settings", data=DashData(), bsdata=FetchBSData(), session=session, config=UserConfig)
        if request.method == "POST":
            try:
                BSPostHandler([request.form["banchoman"], request.form["mainmemuicon"], request.form["loginnotif"]], session) #handles all the changes
                return render_template("banchosettings.html", preset=FetchBSData(), title="Bancho Settings", data=DashData(), bsdata=FetchBSData(), session=session, config=UserConfig, success="Bancho settings were successfully edited!")
            except Exception as e:
                print(e)
                ConsoleLog("Error while editing bancho settings!", f"{e}", 3)
                return render_template("banchosettings.html", preset=FetchBSData(), title="Bancho Settings", data=DashData(), bsdata=FetchBSData(), session=session, config=UserConfig, error="An internal error has occured while saving bancho settings! An error has been logged to the console.")

    else:
        return NoPerm(session, request.url)

""" 통합 리더보드 """
@app.route("/frontend/leaderboard")
#아 국가별 리더보드 만들기 존나 귀찮다
def leaderboard():
    rx = request.args.get("rx")
    mode = request.args.get("mode")
    board = request.args.get("board")
    if rx is None:
        return redirect(f"https://admin.{ServerDomain}/frontend/leaderboard?rx=0&mode=0&board=0")
    elif mode is None:
        return redirect(f"https://admin.{ServerDomain}/frontend/leaderboard?rx={rx}&mode=0&board=0")
    elif board is None:
        return redirect(f"https://admin.{ServerDomain}/frontend/leaderboard?rx={rx}&mode={mode}&board=0")
    elif int(mode) > 3:
        return "WHAT IS THAT MODE?"

    if int(mode) == 0:
        mode = "std"
    elif int(mode) == 1:
        mode = "taiko"
    elif int(mode) == 2:
        mode = "ctb"
    elif int(mode) == 3:
        mode = "mania"
    else:
        mode = "std"

    if int(rx) == 0:
        table = "users_stats"
        rx = "vn"
        tt = "Vanilla"
    elif int(rx) == 1:
        table = "rx_stats"
        rx = "rx"
        tt = "Relax"
    elif int(rx) == 2:
        table = "ap_stats"
        rx = "ap"
        tt = "Autopilot"
    else:
        table = "users_stats"
        rx = "vn"
        tt = "Vanilla"

    sql = f"SELECT {table}.country, {table}.id, {table}.username, {table}.pp_{mode}, {table}.ranked_score_{mode}, {table}.avg_accuracy_{mode}, {table}.playcount_{mode}, {table}.level_{mode} FROM {table} LEFT JOIN users ON users.id = {table}.id WHERE users.privileges NOT IN (0) AND users.privileges NOT IN (2) AND users.id != 999 "

    if int(board) == 0:
        sql += f"ORDER BY pp_{mode} DESC, ranked_score_{mode} DESC, avg_accuracy_{mode} DESC, level_{mode} DESC, playcount_{mode} DESC, {table}.id"
        board = "pp"
    elif int(board) == 1:
        sql += f"ORDER BY ranked_score_{mode} DESC, pp_{mode} DESC, avg_accuracy_{mode} DESC, level_{mode} DESC, playcount_{mode} DESC, {table}.id"
        board = "score"
    elif int(board) == 2:
        sql += f"ORDER BY avg_accuracy_{mode} DESC, pp_{mode} DESC, ranked_score_{mode} DESC, level_{mode} DESC, playcount_{mode} DESC, {table}.id"
        board = "Accuracy"
    elif int(board) == 3:
        sql += f"ORDER BY playcount_{mode} DESC, pp_{mode} DESC, ranked_score_{mode} DESC, avg_accuracy_{mode} DESC, level_{mode} DESC, {table}.id"
        board = "Playcount"
    elif int(board) == 4:
        sql += f"ORDER BY level_{mode} DESC, pp_{mode} DESC, ranked_score_{mode} DESC, avg_accuracy_{mode} DESC, playcount_{mode} DESC, {table}.id"
        board = "level"

    mycursor.execute(sql)
    lb = mycursor.fetchall()
    log.info(f"{mode} {rx} 리더보드 {board} 정렬")

    ReadableArray = []
    if len(lb) > 1:
        for i, x in enumerate(lb):
            Dicti = {}
            Dicti["Rank"] = i + 1

            Dicti["Country"] = x[0]
            Dicti["PlayerId"] = x[1]
            Dicti["Player"] = x[2]

            Dicti["pp"] = f"{round(x[3], 2):,}"
            Dicti["Score"] = f'{x[4]:,}'

            Dicti["Accuracy"] = f"{round(x[5], 2):,}"

            Dicti["Playcount"] = f"{x[6]:,}"
            Dicti["Level"] = f"{x[7]}"

            ReadableArray.append(Dicti)
    
    return render_template("leaderboard.html", data=DashData(), session=session, title=f"{tt} Leaderboard", config=UserConfig, StatData = ReadableArray, type = f"ORDER by {board}_{mode}")

""" ranked_status http + rankedby"""
@app.route("/frontend/ranked_status/<id>")
def ranked_status(id):
    mycursor.execute("SELECT ranked, rankedby FROM beatmaps WHERE beatmap_id = %s", [id])
    try:
        result = mycursor.fetchone()
        redstar_ranked = result[0]
        rankedby = result[1]
        if redstar_ranked == 2:
            redstar_ranked = [rankedby, "Ranked", 2]
        elif redstar_ranked == 5:
            redstar_ranked = [rankedby, "Loved", 5]
        elif redstar_ranked == 3:
            redstar_ranked = [rankedby, "Approved", 3]
        elif redstar_ranked == 4:
            redstar_ranked = [rankedby, "Qualified", 4]
        elif redstar_ranked == 0:
            redstar_ranked = [rankedby, "Unranked", 0]
    except Exception as e:
        log.error(f"{id} redstar_ranked_status 조회 실패! | {e}")
        redstar_ranked = None

    try:
        bancho_ranked = int(requests.get(f'https://osu.ppy.sh/api/get_beatmaps?k={UserConfig["APIKey"]}&b={id}', headers=requestHeaders).json()[0]["approved"])
        if bancho_ranked == 1:
            bancho_ranked = ["Ranked", 1]
        elif bancho_ranked == 4:
            bancho_ranked = ["Loved", 4]
        elif bancho_ranked == 2:
            bancho_ranked = ["Approved", 2]
        elif bancho_ranked == 3:
            bancho_ranked = ["Qualified", 3]
        elif bancho_ranked == 0:
            bancho_ranked = ["Pending (Unranked)", 0]
        elif bancho_ranked == -1:
            bancho_ranked = ["WIP (Unranked)", -1]
        elif bancho_ranked == -2:
            bancho_ranked = ["Graveyard (Unranked)", -2]
    except:
        log.error(f"{id} bancho_ranked_status 조회 실패!")
        bancho_ranked = None

    return {"redstar": redstar_ranked, "bancho": bancho_ranked}

#/rank/<id> 요청시 id가 bid, bsid 둘다 DB에 존재할경우 선택 페이지
@app.route("/rank/select/<id>")
def RankMap_select(id):
    log.debug("/ranked/select/<id> 요청 완료")
    mycursor.execute("SELECT rankedby FROM beatmaps WHERE beatmap_id = %s", [id])
    rankedby = mycursor.fetchone()
    
    return render_template("search_beatmap.html", title="Searched Beatmap!", data=DashData(), session=session, config=UserConfig, song_query = id, SuggestedBmaps2 = SplitList(SearchBeatmap(id, rank_select = True)))
    #return render_template("beatrank_select.html", title="Select Beatmap!", data=DashData(), session=session, beatdata=SplitList(GetBmapInfo(id)), config=UserConfig, Id= id)

@app.route("/rank/<id>", methods = ["GET", "POST"])
def RankMap(id):
    #비트맵셋 요청시 리다이렉트
    mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = %s", [id])
    check_beatmapSet = mycursor.fetchone()

    #비트맵셋 요청시 리다이렉트 --> 혹시나 DB중복감지
    mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmap_id = %s", [id])
    check_beatmap = mycursor.fetchone()

    if check_beatmapSet is not None and check_beatmap is not None:
        log.debug(f"{id} 는 비트맵셋, 비트맵 둘다 존재함")
        log.debug("비트맵 선택 페이지 리다이렉트")
        return redirect(f"/rank/select/{id}")

    #비트맵셋 요청시 리다이렉트
    if check_beatmapSet is not None:
        log.warning(f"/rank/{id} 에서 비트맵셋 감지.")
        log.warning(f"/rank/{check_beatmapSet[0]} 로 리다이렉트.")
        return redirect(f"/rank/{check_beatmapSet[0]}")

    if HasPrivilege(session["AccountId"], 3):
        if request.method == "GET":
            return render_template("beatrank.html", title="Rank Beatmap!", data=DashData(), session=session, beatdata=SplitList(GetBmapInfo(id)), config=UserConfig, Id= id)
        if request.method == "POST":
            try:
                BeatmapNumber = request.form["beatmapnumber"]
                RankBeatmap(BeatmapNumber, request.form[f"bmapid-{BeatmapNumber}"], request.form[f"rankstatus-{BeatmapNumber}"], session)
               
                #rankedby 추가
                beatmap_rankedby("BeatmapID", request.form[f"bmapid-{BeatmapNumber}"])

                return render_template("beatrank.html", title="Rank Beatmap!", data=DashData(), session=session, beatdata=SplitList(GetBmapInfo(id)), config=UserConfig, success=f"Successfully ranked beatmap {id}!", Id= id)
            except Exception as e:
                print(e)
                ConsoleLog(f"Error while ranking beatmap ({id})!", f"{e}", 3)
                return render_template("beatrank.html", title="Rank Beatmap!", data=DashData(), session=session, beatdata=SplitList(GetBmapInfo(id)), config=UserConfig, error="An internal error has occured while ranking! An error has been logged to the console.", Id= id)
    else:
        return NoPerm(session, request.url)

@app.route("/rank", methods = ["GET", "POST"])
def RankFrom():
    if request.method == "GET":
        if HasPrivilege(session["AccountId"], 3):
            return render_template("rankform.html", title="Rank a beatmap!", data=DashData(), session=session, config=UserConfig, SuggestedBmaps = SplitList(GetSuggestedRank()))
        else:
            return NoPerm(session, request.url)
    else:
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
            return NoPerm(session, request.url)
        else:
            return redirect(f"/rank/{request.form['bmapid']}") #does this even work


#/rank/search 추가
def SearchBeatmap(song_query, rank_select = False):
    log.debug("/rank/<id>에서 DB에 bid, bsid 둘다 존재할 겅우, rank_select = {}".format(rank_select))
    #/rank/<id>에서 DB에 bid, bsid 둘다 존재할 겅우
    if rank_select:
        Beatmaps = [0, 0]

        #bid
        mycursor.execute("SELECT beatmapset_id FROM beatmaps WHERE beatmap_id = %s", [song_query])
        bsid = mycursor.fetchone()[0]
        mycursor.execute("SELECT beatmap_id, song_name, beatmapset_id, rankedby FROM beatmaps WHERE beatmapset_id = %s", [bsid])
        a = mycursor.fetchall()[0]
        Beatmaps[0] = a

        #bsid
        mycursor.execute("SELECT beatmap_id, song_name, beatmapset_id, rankedby FROM beatmaps WHERE beatmapset_id = %s", [song_query])
        a2 = mycursor.fetchall()[0]
        Beatmaps[1] = a2
    else:
        #기존 곡 서치 (비트맵 이름)
        mycursor.execute("SELECT beatmap_id, song_name, beatmapset_id, rankedby FROM beatmaps WHERE song_name LIKE %s GROUP BY beatmapset_id", [f"%{song_query}%"])
        Beatmaps = mycursor.fetchall()

    BeatmapList = []

    for TopBeatmap in Beatmaps:

        r = requests.get(f'https://cheesegull.{ServerDomain}/api/s/{TopBeatmap[2]}', headers=requestHeaders)
        log.info("/rank/search 쿼리 cheesegull 비트맵셋 = {} 조회 (맵 제작자 가져오는 코드)".format(TopBeatmap[2]))
        r = r.json()

        try:
            Creator = r["Creator"]
        except:
            Creator = "ERROR Not Found!"

        BeatmapList.append({
            "BeatmapId" : TopBeatmap[0],
            "BeatmapSetId" : TopBeatmap[2],
            "SongName" : TopBeatmap[1],
            "Cover" : f"https://b.{ServerDomain}/bg/{TopBeatmap[0]}",
            #"Cover" : f"https://assets.ppy.sh/beatmaps/{TopBeatmap[2]}/covers/cover.jpg",
            "Creator" : Creator,
            "Rankedby" : TopBeatmap[3],
            "Beatmaps_count" : len(Beatmaps)
        })
    
    log.info("{} 검색완료".format(song_query))

    return BeatmapList

""" pwreset http """
@app.route("/frontend/pwreset/<id>", methods = ["GET", "POST"])
def pw_reset(id):
    idontknowemail = f"https://{ServerDomain}/settings"

    mycursor.execute("SELECT username FROM users WHERE id = %s", [id])
    username = mycursor.fetchone()[0]

    mycursor.execute("SELECT id, k, u, t FROM password_recovery WHERE u = %s AND k LIKE 'Realistik Panel : %' ORDER BY id DESC LIMIT 1", [username])
    info = mycursor.fetchone()
    if info is None: noRecoveryData = True
    else:
        noRecoveryData = False
        exfireDate = int(info[3].timestamp()) + 300
        nowDate = time.time()
        key = info[1].replace("Realistik Panel : ", "")
        
        #html에서 ttl 쿼리로 요청시 ttl만 반환
        ttlRequest = request.args.get("ttl")
        if ttlRequest is not None:
            ttl = int(exfireDate - nowDate)
            return Response(json.dumps({"ttl": ttl, "query": ttlRequest}, indent=2, ensure_ascii=False), content_type='application/json')
        
        if exfireDate < nowDate:
            noRecoveryData = True
            mycursor.execute("DELETE FROM password_recovery WHERE u = %s AND k LIKE 'Realistik Panel : %' ORDER BY id DESC LIMIT 1", [username])
            mydb.commit()

            log.warning("비번 재설정 키 만료됨!")
            html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Password Changed!</title>
                    <meta http-equiv="refresh" content="3;url=https://admin.{ServerDomain}/frontend/pwreset/{id}">
                </head>
                <body>
                    <h1 style="text-align: center;">Key Exfired! Redirect pwreset page after 3sec</h1>
                </body>
                </html>
            """
            return html

    if request.method == "GET":
        if noRecoveryData:
            code = sendPwresetMail(session, id)
            return render_template("pwreset_confirm.html", title="Verifying!", data=DashData(), session=session, success="Check Your Email!", config=UserConfig, code=code, idontknowemail=idontknowemail, password=None, ck=False)
        else:
            return render_template("pwreset_confirm.html", title="Verifying! 22", data=DashData(), session=session, success="Check Your Email! 22", config=UserConfig, code=key, idontknowemail=idontknowemail, password=None, ck=False)
    else:
        #위에 GET에서 들어오는 요청과 POST에서 다시 POST로 들어오는 요청 2개임
        try:
            code = request.form["code"]
        except:
            code = ""

        try:
            password = request.form["password"]
            #ChangePassword(id, password)
            ChangePWForm(form={"accid": id, "newpass": password}, session={"AccountId": id})

            mycursor.execute("DELETE FROM password_recovery WHERE u = %s AND k LIKE 'Realistik Panel : %' ORDER BY id DESC LIMIT 1", [username])
            mydb.commit()

            html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Password Changed!</title>
                    <meta http-equiv="refresh" content="3;url=https://{ServerDomain}/login">
                </head>
                <body>
                    <h1 style="text-align: center;">password changed!! Redirect login page after 3sec</h1>
                </body>
                </html>
            """

            return html
            return render_template("pwreset_confirm.html", title="Password Changed!", data=DashData(), session=session, success="Password Changed!", config=UserConfig, code=code, idontknowemail=idontknowemail, password=password, ck=True) 
        except:
            password = None

        if code == key:
            if exfireDate > nowDate: 
                return render_template("pwreset_confirm.html", title="Reset Password!", data=DashData(), session=session, config=UserConfig, code=code, idontknowemail=idontknowemail, password=password, ck=True)
            else:
                log.warning("비번 재설정 키 만료됨!")
                mycursor.execute("DELETE FROM password_recovery WHERE id = %s AND k LIKE 'Realistik Panel : %'", [info[0]])
                mydb.commit()

                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Password Changed!</title>
                    <meta http-equiv="refresh" content="3;url=https://admin.{ServerDomain}/frontend/pwreset/{id}">
                </head>
                <body>
                    <h1 style="text-align: center;">Key Exfired! Redirect pwreset page after 3sec</h1>
                </body>
                </html>
            """

            return html
        else:
            return render_template("pwreset_confirm.html", title="Wrong Key!", data=DashData(), session=session, error="Wrong Key!", config=UserConfig, code=code,idontknowemail=idontknowemail, password=None, ck=False)

""" pwreset http """
@app.route("/frontend/pwreset", methods = ["GET", "POST"])
def get_pw_reset():
    if request.method == "POST":
        userinfo = request.form["userinfo"]
        try:
            userID = int(userinfo) #ID인 경우
        except:
            log.error(f"userinfo 는 숫자가 아님 | {userinfo}")
            userID = FindUserByUsername(userinfo, 1) #username, email인 경우
            if len(userID) == 0:
                log.error(f"user Not Found! | {userinfo}")
                return f"user Not Found! | {userinfo}"
            userID = userID[0]["Id"]

        return redirect(f"/frontend/pwreset/{userID}") #does this even work
    else:
        return render_template("pwreset.html", title="Reset Password!", data=DashData(), session=session, config=UserConfig)

""" pwreset http """
@app.route("/frontend/namereset/<id>", methods = ["GET", "POST"])
def name_reset(id):
    #html에서 ttl 쿼리로 요청시 ttl만 반환
    ttlRequest = request.args.get("ttl")
    if ttlRequest is not None:
        ttl = r.ttl(f"RealistikPanel:UsernameResetMailAuthKey:{id}")
        return Response(json.dumps({"ttl": ttl, "query": ttlRequest}, indent=2, ensure_ascii=False), content_type='application/json')

    idontknowemail = f"https://{ServerDomain}/settings"
    
    try:
        key = r.get(f"RealistikPanel:UsernameResetMailAuthKey:{id}").decode("utf-8")
    except:
        key = None

    """ if key is None:
        noRecoveryData = True
    else:
        noRecoveryData = False """

    if request.method == "GET":
        if key is None:
            code = sendUsernameresetMail(session, id)
            if type(code) != str:
                return Response(json.dumps({"code": str(code), "msg": "Mail Send ERROR!! Please report to admin!!"}, indent=2, ensure_ascii=False), status=500, content_type='application/json') 
            return render_template("namereset_confirm.html", title="Verifying!", data=DashData(), session=session, success="Check Your Email!", config=UserConfig, code=code, idontknowemail=idontknowemail, username=None, ck=False)
        else:
            return render_template("namereset_confirm.html", title="Verifying! 22", data=DashData(), session=session, success="Check Your Email! 22", config=UserConfig, code=key, idontknowemail=idontknowemail, username=None, ck=False)
    else:
        #위에 GET에서 들어오는 요청과 POST에서 다시 POST로 들어오는 요청 2개임
        try:
            code = request.form["code"]
        except:
            code = ""

        try:
            NewUsername = request.form["NewUsername"]

            CU = ChangeUsername(id, NewUsername)
            if CU["code"]:
                r.delete(f"RealistikPanel:UsernameResetMailAuthKey:{id}")

                html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Username Changed!</title>
                        <meta http-equiv="refresh" content="3;url=https://{ServerDomain}/login">
                    </head>
                    <body>
                        <h1 style="text-align: center;">username changed!! Redirect login page after 3sec</h1>
                    </body>
                    </html>
                """

                return html
                return render_template("namereset_confirm.html", title="Password Changed!", data=DashData(), session=session, success="Password Changed!", config=UserConfig, code=code, idontknowemail=idontknowemail, username=NewUsername, ck=True) 
            else:
                return render_template("namereset_confirm.html", title="Wrong Key!", data=DashData(), session=session, error=CU["msg"], config=UserConfig, code=code, idontknowemail=idontknowemail, username=None, ck=True)
        except:
            NewUsername = None

        if key:
            if code == key:
                return render_template("namereset_confirm.html", title="Input Your NewUsername!", data=DashData(), session=session, config=UserConfig, code=code, idontknowemail=idontknowemail, username=NewUsername, ck=True)
            else:
                return render_template("namereset_confirm.html", title="Wrong Key!", data=DashData(), session=session, error="Wrong Key!", config=UserConfig, code=code, idontknowemail=idontknowemail, username=None, ck=False)
        else:
            log.warning("비번 재설정 키 만료됨!")
            r.delete(f"RealistikPanel:UsernameResetMailAuthKey:{id}")

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Username Changed!</title>
                <meta http-equiv="refresh" content="3;url=https://admin.{ServerDomain}/frontend/namereset/{id}">
            </head>
            <body>
                <h1 style="text-align: center;">Key Exfired! Redirect namereset page after 3sec</h1>
            </body>
            </html>
        """

        return html

""" pwreset http """
@app.route("/frontend/namereset", methods = ["GET", "POST"])
def get_name_reset():
    if request.method == "POST":
        userinfo = request.form["userinfo"]
        try:
            userID = int(userinfo) #ID인 경우
        except:
            log.error(f"userinfo 는 숫자가 아님 | {userinfo}")
            userID = FindUserByUsername(userinfo, 1) #username, email인 경우
            if len(userID) == 0:
                log.error(f"user Not Found! | {userinfo}")
                return f"user Not Found! | {userinfo}"
            userID = userID[0]["Id"]

        return redirect(f"/frontend/namereset/{userID}") #does this even work
    else:
        return render_template("namereset.html", title="Reset Username!", data=DashData(), session=session, config=UserConfig)

@app.route("/rank/search/<song_query>")
def SearchMap(song_query):
    if HasPrivilege(session["AccountId"], 3):

        log.info("{} 검색중".format(song_query))

        return render_template("search_beatmap.html", title="Searched Beatmap!", data=DashData(), session=session, config=UserConfig, song_query = song_query, SuggestedBmaps2 = SplitList(SearchBeatmap(song_query)))
    else:
        return NoPerm(session, request.url)

@app.route("/rank/search", methods = ["GET", "POST"])
def SearchMap_Post():
    if request.method == "POST":
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
                return NoPerm(session, request.url)
        else:
            return redirect(f"/rank/search/{request.form['songname']}") #does this even work
    else:
        return redirect(f"/rank")

@app.route("/verify_video")
def Verify_videos_tool():
    if HasPrivilege(session["AccountId"], 6):
        return render_template("verify_video_tool.html", title="verify_video_tool", data=DashData(), session=session, config=UserConfig)
    else: return NoPerm(session, request.url)

@app.route("/testaccount_build")
def TestAccountBuild():
    if HasPrivilege(session["AccountId"], 6):
        tsac = request.args.get("ts", 1014)
        target = request.args.get("target", 0)
        if tsac == target: return "NO"

        FokaMessage({"k": UserConfig['FokaKey'], "fro": None, "to": "#osu", "msg": "!vbri 1"})
        newUsername = f"test{target}"
        CU = ChangeUsername(tsac, newUsername)
        if not CU["code"]: return CU
        ChangePWForm(form={"accid": tsac, "newpass": newUsername}, session={"AccountId": tsac})
        WipeAccount(tsac)

        mycursor.execute("SELECT h.mac, h.unique_id, h.disk_id, u.notes FROM users AS u JOIN hw_user AS h ON u.id = h.userid WHERE u.id = %s", [target])
        notes = mycursor.fetchone(); notes = f"{notes[0]}:{notes[1]}:{notes[2]}\n\n\n{notes[3]}"
        q = [newUsername] * 3 + [notes, target]
        mycursor.execute("UPDATE users AS u JOIN hw_user AS h ON u.id = h.userid SET h.mac = %s, h.unique_id = %s, h.disk_id = %s, h.activated = 0, u.notes = %s WHERE u.id = %s", q)
        mydb.commit()
        return newUsername
    else: return NoPerm(session, request.url)


def tsARb(session, request, migration=True):
    if HasPrivilege(session["AccountId"], 6):
        tsac = request.args.get("ts", 1014)
        target = request.args.get("target", 1014)
        if tsac == target: return "NO"

        FokaMessage({"k": UserConfig['FokaKey'], "fro": None, "to": "#osu", "msg": "!vbri 0"})
        if migration:
            log.info(f"migration = {migration}")
            for sc in ["", "_relax", "_ap"]:
                log.info(f"scores{sc} 테이블 작업중...")
                mycursor.execute(f"UPDATE scores{sc} SET userid = %s WHERE userid = %s", [target, tsac]) #ts --> origin 이식
                mydb.commit()
                mycursor.execute(f"SELECT id, beatmap_md5, play_mode, COUNT(*) AS cnt FROM scores{sc} WHERE userid = %s AND completed = 3 GROUP BY beatmap_md5, completed HAVING cnt > 1", [target]) #중복점수 beatmap_md5 값 가져옴
                for i in mycursor.fetchall():
                    log.info(i)
                    mycursor.execute(f"UPDATE scores{sc} SET completed = 2 WHERE userid = %s AND beatmap_md5 = %s AND play_mode = %s AND completed = 3", [target, i[1], i[2]]) #completed 2 일괄 변경
                    mycursor.execute(f"SELECT id FROM scores{sc} WHERE userid = %s AND beatmap_md5 = %s AND play_mode = %s ORDER BY pp DESC LIMIT 1", [target, i[1], i[2]]) #pp 최고기록 id 가져옴
                    mycursor.execute(f"UPDATE scores{sc} SET completed = 3 WHERE id = %s", [mycursor.fetchone()[0]]) #베퍼포 설정
                    mydb.commit()
        else: log.info(f"migration = {migration}")

        CU = ChangeUsername(tsac, UserConfig["TestAccountInfo"]["name"])
        if not CU["code"]: return CU
        ChangePWForm(form={"accid": tsac, "newpass": UserConfig["TestAccountInfo"]["pass"]}, session={"AccountId": tsac})
        WipeAccount(tsac)

        try:
            mycursor.execute("SELECT notes FROM users WHERE id = %s", [target])
            hw, notes = mycursor.fetchone()[0].split("\n\n\n", 1)
            q = hw.split(":") + [notes, target]
            mycursor.execute("UPDATE users AS u JOIN hw_user AS h ON u.id = h.userid SET h.mac = %s, h.unique_id = %s, h.disk_id = %s, h.activated = 1, u.notes = %s WHERE u.id = %s", q)
            mydb.commit()
        except Exception as e: log.warning(f"{e}\n\n{target} ID 는 hw_info 복원 필요 없다고 판?단함")
        return "ok"
    else: return NoPerm(session, request.url)

@app.route("/testaccount_migration")
def TestAccountMigration(): return tsARb(session, request, migration=True)

@app.route("/testaccount_rollback")
def TestAccountRollback(): return tsARb(session, request, migration=False)

@app.route("/upload_verify_video", methods = ["GET", "POST"])
def uploadVerifyVideo():
    if not os.path.exists("verifyVideos"): os.makedirs("verifyVideos")
    isupload = request.args.get("upload",  False)
    isview = request.args.get("view",  False)
    if request.method == "POST":
        ID = request.form.get("ID", None)
        file = request.files.get("File", None)
        mycursor.execute("SELECT username FROM users WHERE id = %s", [ID])
        username = mycursor.fetchone()[0]

        ALLOWED_EXTENSIONS = {"avi", "mp4", "ogv", "ts", "webm", "flv", "wmv", "mkv", "mov"}
        if file.filename.split(".")[-1].lower() not in ALLOWED_EXTENSIONS:
            return f"Invalid file type. Only video files are allowed.\n{ALLOWED_EXTENSIONS}", 400
        video = sorted([i for i in os.listdir("verifyVideos") if i.startswith(f"{username}({ID})")], key=lambda x: int(x.split('-')[1].split('.')[0]), reverse=True)
        if len(video) >= 3: return "Upload limit exceeded.", 403

        file.save(f"verifyVideos/{username}({ID})-{round(time.time())}.{file.filename.split('.')[-1]}")
        RAPLog(ID, f"has Upload Verify Video {UserConfig['ServerURL'].replace('://', '://admin.')}upload_verify_video?view={ID}")
        return redirect(url_for("uploadVerifyVideo", view=ID))
    else:
        if type(isupload) is str: return render_template("upload_verify_video.html", title="upload verify video", data=DashData(), session=session, config=UserConfig)
        elif type(isview) is str and isview:
            item = int(request.args.get("p",  1))
            mycursor.execute("SELECT username FROM users WHERE id = %s", [isview])
            username = mycursor.fetchone()[0]
            video = sorted([i for i in os.listdir("verifyVideos") if i.startswith(f"{username}({isview})")], key=lambda x: int(x.split('-')[1].split('.')[0]), reverse=True)

            if not video or len(video) < item: return NotFoundError(None)

            if request.headers.get('Range', None): Range = request.headers.get('Range').replace("bytes=", "").split("-")
            else: Range = ["0", ""]
            fileSize = os.path.getsize(f"verifyVideos/{video[item - 1]}")
            start = int(Range[0])
            end = fileSize - 1 if not Range[1] else int(Range[1])
            contentLength = end - start + 1

            with open(f"verifyVideos/{video[item - 1]}", "rb") as f:
                f.seek(start)
                file = f.read(contentLength) if start != 0 or (start == 0 and Range[1]) else f.read()
            ptct = requests.get(f"https://b.{ServerDomain}/content-type?q=verifyVideos/{video[item - 1]}", headers=requestHeaders, timeout=3)
            ptct = ptct.json()["msg"]["Content-Type"] if ptct.status_code == 200 else "video/mp4"
            response = Response(file, status=206, mimetype=ptct)
            response.headers['Content-Disposition'] = f'inline; filename="{video[item - 1]}"'
            response.headers['Accept-Ranges'] = "bytes"
            response.headers['Content-Range'] = f'bytes {start}-{end}/{fileSize}'
            response.headers['Content-Length'] = contentLength
            return response
        else: return render_template("upload_verify_video_select.html", title="upload verify video select", data=DashData(), session=session, config=UserConfig)

@app.route("/banmailtemple")
def banmailTemplates():
    username = request.args.get("username", "Devlant")
    beatmapInfo = json.loads(request.args.get("beatmapInfo", {"bid": 0, "beatmapInfo": None}))
    country = request.args.get("country", "XX")
    return banEmailBody(country, username, beatmapInfo)

@app.route("/sendautobanmail", methods = ["GET", "POST"])
def send_auto_ban_mail():
    userID = request.args.get("uid")
    if userID is None:
        return Response(json.dumps({"code": 403, "message": "No Query"}, indent=2, ensure_ascii=False), content_type='application/json')
    else:
        userID = int(userID)

    AuthKey = request.headers.get("AuthKey")
    if AuthKey is None:
        return Response(json.dumps({"code": 403, "message": "No AuthKey"}, indent=2, ensure_ascii=False), content_type='application/json')

    BI = request.headers.get("beatmapInfo")
    if BI is None:
        return Response(json.dumps({"code": 403, "message": "No BeatmapInfo"}, indent=2, ensure_ascii=False), content_type='application/json')
    else:
        BI = json.loads(BI)

    mycursor.execute("SELECT email FROM users WHERE id = %s", [userID])
    email = mycursor.fetchone()[0]

    if request.method == "GET":
        return f"Yo, GET is not Work! \nuserID = {userID} | AuthKey = {AuthKey} | email = {email} | BI = {BI}"
    else:
        sc = sendAutoBanMail(session, AuthKey, userID, email, BI)
        if sc != 200:
            msg = {"code": sc, "message": {200: "OK", 403: "AuthKey Not Matched", 404: "AuthKey Not Found in Redis", 503: "Failed mail send", 500: "Failed copy mail to Sent folder"}}
            log.warning(msg)
            return Response(json.dumps(msg, indent=2, ensure_ascii=False), content_type='application/json')
        return "OK"

@app.route("/sendbanmail", methods = ["GET", "POST"])
def send_ban_mail():
    if request.method == "GET":
        if HasPrivilege(session["AccountId"]):
            return render_template("sendbanmail.html", title="Send Ban Mail", data=DashData(), session=session, config=UserConfig)
        else:
            return NoPerm(session, request.url)
    else:
        if HasPrivilege(session["AccountId"]):
            userID = request.form["userid"]
            mycursor.execute("SELECT email FROM users WHERE id = %s", [userID])
            email = mycursor.fetchone()[0]
            beatmapInfo = {"bid": request.form["bid"], "beatmapInfo": request.form["msg"]}
            sendBanMail(session, userID, email, beatmapInfo)
            return render_template("sendbanmail.html", title="Send Ban Mail", data=DashData(), session=session, config=UserConfig, success=f"Successfully Send Ban mail! to {email}")
        else:
            return NoPerm(session, request.url)

@app.route("/sendemail", methods = ["GET", "POST"])
def send_mail():
    if request.method == "GET":
        if HasPrivilege(session["AccountId"]):
            return render_template("sendemail.html", title="Send Email", data=DashData(), session=session, config=UserConfig)
        else:   
            return NoPerm(session, request.url)
    else:
        if HasPrivilege(session["AccountId"]):
            nick = request.form["nickname"]
            email = request.form["email"]
            subject = request.form["subject"]
            msg = request.form["msg"]
            MIMEType = "html" if request.form['mailType'] == "0" else "plain"

            sendEmail(session, nick, email, subject, msg, MIMEType)
            return render_template("sendemail.html", title="Send Email", data=DashData(), session=session, config=UserConfig, success=f"Successfully Send Email! to {email}")
        else:
            return NoPerm(session, request.url)


@app.route("/users/<page>", methods = ["GET", "POST"])
def Users(page = 1):
    if HasPrivilege(session["AccountId"], 6):
        mycursor.execute("SELECT privileges, name FROM privileges_groups")
        privilegesList = mycursor.fetchall()
        mycursor.execute("SELECT id, name FROM badges")
        badgesList = mycursor.fetchall()

        if request.method == "GET":
            selected = session.get("selected", ["", -1, -1, "-1"])
            UserData = FindUserByUsername(selected[0], int(page), selected)
            #return render_template("users.html", title="Users", data=DashData(), session=session, config=UserConfig, UserData = FetchUsers(int(page)-1), page=int(page), selected=selected, privilegesList=privilegesList, badgesList=badgesList, Pages=UserPageCount(selected))
            return render_template("users.html", title="Users", data=DashData(), session=session, config=UserConfig, UserData=UserData, page=int(page), selected=selected, privilegesList=privilegesList, badgesList=badgesList, Pages=UserPageCount(selected))       
        if request.method == "POST":
            session["selected"] = [ #사용자 선택 값을 세션에 저장
                str(request.form.get("user", "")),
                int(request.form.get("privilege", -1)),
                int(request.form.get("badge", -1)),
                str(request.form.get("country", "-1"))
            ]
            selected = session.get("selected")
            UserData = FindUserByUsername(selected[0], int(page), selected)
            #return render_template("users.html", title="Users", data=DashData(), session=session, config=UserConfig, UserData = FindUserByUsername(request.form["user"], int(page), int(request.form["privilege"]), int(request.form["badge"]), request.form["country"]), page=int(page), User=request.form["user"], selected=session.get('selected', [-1, -1, -1]), privilegesList=privilegesList, badgesList=badgesList, Pages=UserPageCount())
            return render_template("users.html", title="Users", data=DashData(), session=session, config=UserConfig, UserData=UserData, page=int(page), User=request.form["user"], selected=selected, privilegesList=privilegesList, badgesList=badgesList, Pages=UserPageCount(selected))
    else:
        return NoPerm(session, request.url)

@app.route("/index.php")
def LegacyIndex():
    """For implementing RAP funcions."""
    Page = request.args.get("p")
    if Page == "124":
        #ranking page
        return redirect(f"/rank/{request.args.get('bsid')}")
    elif Page == "103": #hanayo link
        Account = request.args.get("id")
        return redirect(f"/user/edit/{Account}")
    return redirect(url_for("dash")) #take them to the root

@app.route("/system/settings", methods = ["GET", "POST"])
def SystemSettings():
    if HasPrivilege(session["AccountId"], 4):
        if request.method == "GET":
            return render_template("syssettings.html", data=DashData(), session=session, title="System Settings", SysData=SystemSettingsValues(), config=UserConfig)
        if request.method == "POST":
            try:
                ApplySystemSettings([request.form["webman"], request.form["gameman"], request.form["register"], request.form["globalalert"], request.form["homealert"]], session) #why didnt i just pass request
                return render_template("syssettings.html", data=DashData(), session=session, title="System Settings", SysData=SystemSettingsValues(), config=UserConfig, success = "System settings successfully edited!")
            except Exception as e:
                print(e)
                ConsoleLog("Error while editing system settings!", f"{e}", 3)
                return render_template("syssettings.html", data=DashData(), session=session, title="System Settings", SysData=SystemSettingsValues(), config=UserConfig, error = "An internal error has occured while saving system settings! An error has been logged to the console.")
        else:
            return NoPerm(session, request.url)

@app.route("/user/edit/<id>", methods = ["GET", "POST"])
def EditUser(id):
    def client_ver():
        mycursor.execute("SELECT osuver FROM users WHERE id = %s", [id])
        osuver = mycursor.fetchone()[0]
        mycursor.execute("SELECT privileges, COUNT(*) AS cnt FROM users WHERE osuver = %s AND privileges IN (0, 2) GROUP BY privileges", [osuver])
        cnt = mycursor.fetchall()
        if len(cnt) == 0: cnt = "Ban : 0, Restrict : 0"
        elif len(cnt) == 1: cnt = f"Ban : {cnt[0][1]}, Restrict : 0"
        elif len(cnt) == 2: cnt = f"Ban : {cnt[0][1]}, Restrict : {cnt[1][1]}"
        else: cnt = f"? : {cnt}"
        return {"ver": osuver, "cnt": cnt}
    def hw_user_info():
        mycursor.execute("SELECT * FROM hw_user WHERE userid = %s", [id])
        return mycursor.fetchone()

    if request.method == "GET":
        if HasPrivilege(session["AccountId"], 6):
            return render_template("edituser.html", data=DashData(), session=session, title="Edit User", config=UserConfig, uid=id, osuver=client_ver(), hw_user_info=hw_user_info(), UserData=UserData(id), Privs = GetPrivileges(), UserBadges= GetUserBadges(id), badges=GetBadges(), ShowIPs = HasPrivilege(session["AccountId"], 16))
        else:
            return NoPerm(session, request.url)
    if request.method == "POST":
        if HasPrivilege(session["AccountId"], 6):
            try:
                ApplyUserEdit(request.form, session)
                RAPLog(session["AccountId"], f"has edited the user {request.form.get('username', 'NOT FOUND')}")
                return render_template("edituser.html", data=DashData(), session=session, title="Edit User", config=UserConfig, uid=id, osuver=client_ver(), hw_user_info=hw_user_info(), UserData=UserData(id), Privs = GetPrivileges(), UserBadges= GetUserBadges(id), badges=GetBadges(), success=f"User {request.form.get('username', 'NOT FOUND')} has been successfully edited!", ShowIPs = HasPrivilege(session["AccountId"], 16))
            except Exception as e:
                print(e)
                ConsoleLog("Error while editing user!", f"{e}", 3)
                return render_template("edituser.html", data=DashData(), session=session, title="Edit User", config=UserConfig, uid=id, osuver=client_ver(), hw_user_info=hw_user_info(), UserData=UserData(id), Privs = GetPrivileges(), UserBadges= GetUserBadges(id), badges=GetBadges(), error="An internal error has occured while editing the user! An error has been logged to the console.", ShowIPs = HasPrivilege(session["AccountId"], 16))
        else:
            return NoPerm(session, request.url)


@app.route("/logs/<page>")
def Logs(page):
    if HasPrivilege(session["AccountId"], 7):
        return render_template("raplogs.html", data=DashData(), session=session, title="Logs", config=UserConfig, Logs = RAPFetch(page), page=int(page), Pages = RapLogCount())
    else:
        return NoPerm(session, request.url)

@app.route("/action/confirm/delete/<id>")
def ConfirmDelete(id):
    """Confirms deletion of acc so accidents dont happen"""
    #i almost deleted my own acc lmao
    #me forgetting to commit changes saved me
    if HasPrivilege(session["AccountId"], 6):
        AccountToBeDeleted = GetUser(id)
        return render_template("confirm.html", data=DashData(), session=session, title="Confirmation Required", config=UserConfig, action=f"delete the user {AccountToBeDeleted['Username']}", yeslink=f"/actions/delete/{id}", backlink=f"/user/edit/{id}")
    else:
        return NoPerm(session, request.url)

@app.route("/user/iplookup/<ip>")
def IPUsers(ip):
    if HasPrivilege(session["AccountId"], 16):
        IPUserLookup  = FindWithIp(ip)
        UserLen = len(IPUserLookup)
        return render_template("iplookup.html", data=DashData(), session=session, title="IP Lookup", config=UserConfig, ipusers=IPUserLookup, IPLen = UserLen, ip=ip)
    else:
        return NoPerm(session, request.url)

@app.route("/badges")
def Badges():
    if HasPrivilege(session["AccountId"], 4):
        return render_template("badges.html", data=DashData(), session=session, title="Badges", config=UserConfig, badges=GetBadges())
    else:
        return NoPerm(session, request.url)

@app.route("/badge/edit/<BadgeID>", methods = ["GET", "POST"])
def EditBadge(BadgeID: int):
    if HasPrivilege(session["AccountId"], 4):
        if request.method == "GET":
            return render_template("editbadge.html", data=DashData(), session=session, title="Edit Badge", config=UserConfig, badge=GetBadge(BadgeID))
        if request.method == "POST":
            try:
                SaveBadge(request.form)
                RAPLog(session["AccountId"], f"edited the badge with the ID of {BadgeID}")
                return render_template("editbadge.html", data=DashData(), session=session, title="Edit Badge", config=UserConfig, badge=GetBadge(BadgeID), success=f"Badge {BadgeID} has been successfully edited!")
            except Exception as e:
                print(e)
                ConsoleLog("Error while editing badge!", f"{e}", 3)
                return render_template("editbadge.html", data=DashData(), session=session, title="Edit Badge", config=UserConfig, badge=GetBadge(BadgeID), error="An internal error has occured while editing the badge! An error has been logged to the console.")
    else:
        return NoPerm(session, request.url)

@app.route("/privileges")
def EditPrivileges():
    if HasPrivilege(session["AccountId"], 13):
        return render_template("privileges.html", data=DashData(), session=session, title="Privileges", config=UserConfig, privileges=GetPrivileges())
    else:
        return NoPerm(session, request.url)

@app.route("/privilege/edit/<Privilege>", methods = ["GET", "POST"])
def EditPrivilege(Privilege: int):
    if HasPrivilege(session["AccountId"], 13):
        if request.method == "GET":
            return render_template("editprivilege.html", data=DashData(), session=session, title="Privileges", config=UserConfig, privileges=GetPriv(Privilege))
        if request.method == "POST":
            try:
                UpdatePriv(request.form)
                Priv = GetPriv(Privilege)
                RAPLog(session["AccountId"], f"has edited the privilege group {Priv['Name']} ({Priv['Id']})")
                return render_template("editprivilege.html", data=DashData(), session=session, title="Privileges", config=UserConfig, privileges=Priv, success=f"Privilege {Priv['Name']} has been successfully edited!")
            except Exception as e:
                print(e)
                ConsoleLog("Error while editing privilege!", f"{e}", 3)
                Priv = GetPriv(Privilege)
                return render_template("editprivilege.html", data=DashData(), session=session, title="Privileges", config=UserConfig, privileges=Priv, error="An internal error has occured while editing the privileges! An error has been logged to the console.")
    else:
        return NoPerm(session, request.url)

@app.route("/console")
def Console():
    if HasPrivilege(session["AccountId"], 14):
        return render_template("consolelogs.html", data=DashData(), session=session, title="Console Logs", config=UserConfig, logs=GetLog())
    else:
        return NoPerm(session, request.url)

@app.route("/changelogs")
def ChangeLogs():
    if HasPrivilege(session["AccountId"]):
        return render_template("changelog.html", data=DashData(), session=session, title="Change Logs", config=UserConfig, logs=Changelogs)
    else:
        return NoPerm(session, request.url)

@app.route("/current.json")
def CurrentIPs():
    """IPs for the Ripple switcher."""
    return jsonify({
        "osu.ppy.sh": UserConfig["CurrentIP"],
        "c.ppy.sh": UserConfig["CurrentIP"],
        "c1.ppy.sh": UserConfig["CurrentIP"],
        "c2.ppy.sh": UserConfig["CurrentIP"],
        "c3.ppy.sh": UserConfig["CurrentIP"],
        "c4.ppy.sh": UserConfig["CurrentIP"],
        "c5.ppy.sh": UserConfig["CurrentIP"],
        "c6.ppy.sh": UserConfig["CurrentIP"],
        "ce.ppy.sh": UserConfig["CurrentIP"],
        "b.ppy.sh": UserConfig["CurrentIP"],
        "a.ppy.sh": UserConfig["CurrentIP"],
        "s.ppy.sh": UserConfig["CurrentIP"],
        "i.ppy.sh": UserConfig["CurrentIP"],
        "bm6.ppy.sh": UserConfig["CurrentIP"]
    })

@app.route("/toggledark")
def ToggleDark():
    if session["Theme"] == "dark":
        session["Theme"] = "white"
    else:
        session["Theme"] = "dark"
    return redirect(url_for("dash"))

@app.route("/admins")
def Admins():
    if HasPrivilege(session["AccountId"]):
        return render_template("admins.html", data=DashData(), session=session, title="Admins", config=UserConfig, admins=SplitList(GetStore()))
    else:
        return NoPerm(session, request.url)


@app.route("/changepass/<AccountID>", methods = ["GET", "POST"]) #may change the route to something within /user
def ChangePass(AccountID):
    if HasPrivilege(session["AccountId"], 6): #may create separate perm for this
        if request.method == "GET":
            User = GetUser(int(AccountID))
            return render_template("changepass.html", data=DashData(), session=session, title=f"Change the Password for {User['Username']}", config=UserConfig, User=User)
        if request.method == "POST":
            ChangePWForm(request.form, session)
            User = GetUser(int(AccountID))
            return redirect(f"/user/edit/{AccountID}")
    else:
        return NoPerm(session, request.url)

@app.route("/donoraward/<AccountID>", methods = ["GET", "POST"])
def DonorAward(AccountID):
    if HasPrivilege(session["AccountId"], 6):
        if request.method == "GET":
            User = GetUser(int(AccountID))
            return render_template("donoraward.html", data=DashData(), session=session, title=f"Award Donor to {User['Username']}", config=UserConfig, User=User)
        if request.method == "POST":
            GiveSupporterForm(request.form)
            User = GetUser(int(AccountID))
            RAPLog(session["AccountId"], f"has awarded {User['Username']} ({AccountID}) {request.form['time']} days of donor.")
            return redirect(f"/user/edit/{AccountID}")
    else:
        return NoPerm(session, request.url)

@app.route("/donorremove/<AccountID>")
def RemoveDonorRoute(AccountID):
    if HasPrivilege(session["AccountId"], 6):
        RemoveSupporter(AccountID, session)
        return redirect(f"/user/edit/{AccountID}")
    else:
        return NoPerm(session, request.url)


@app.route("/rankreq/<Page>")
def RankReq(Page):
    if HasPrivilege(session["AccountId"], 3):
        return render_template("rankreq.html", data=DashData(), session=session, title="Ranking Requests", config=UserConfig, RankRequests = GetRankRequests(int(Page)), page = int(Page))
    else:
        return NoPerm(session, request.url)

@app.route("/clans/<Page>")
def ClanRoute(Page):
    if HasPrivilege(session["AccountId"], 15):
        return render_template("clansview.html", data=DashData(), session=session, title="Clans", config=UserConfig, page = int(Page), Clans = GetClans(Page), Pages = GetClanPages())
    else:
        return NoPerm(session, request.url)

@app.route("/clan/<ClanID>", methods = ["GET", "POST"])
def ClanEditRoute(ClanID):
    if HasPrivilege(session["AccountId"], 15):
        if request.method == "GET":
            return render_template("editclan.html", data=DashData(), session=session, title="Clans", config=UserConfig, Clan=GetClan(ClanID), Members=SplitList(GetClanMembers(ClanID)), ClanOwner = GetClanOwner(ClanID))
        ApplyClanEdit(request.form, session)
        return render_template("editclan.html", data=DashData(), session=session, title="Clans", config=UserConfig, Clan=GetClan(ClanID), Members=SplitList(GetClanMembers(ClanID)), ClanOwner = GetClanOwner(ClanID), success="Clan edited successfully!")
    else:
        return NoPerm(session, request.url)

@app.route("/clan/delete/<ClanID>")
def ClanFinalDelete(ClanID):
    if HasPrivilege(session["AccountId"], 15):
        NukeClan(ClanID, session)
        return redirect("/clans/1")
    return NoPerm(session, request.url)

@app.route("/clan/confirmdelete/<ClanID>")
def ClanDeleteConfirm(ClanID):
    if HasPrivilege(session["AccountId"], 15):
        Clan = GetClan(ClanID)
        return render_template("confirm.html", data=DashData(), session=session, title="Confirmation Required", config=UserConfig, action=f" delete the clan {Clan['Name']}", yeslink=f"/clan/delete/{ClanID}", backlink="/clans/1")
    return NoPerm(session, request.url)



#릴렉 유저별 최근 기록 조회
def RecentPlays_user(text, uid, gamemode = 0, minpp = 0, rx=False, ap=False):
    if rx:
        RXorAP = ["rx", "_relax", ""]
    elif ap:
        RXorAP = ["ap", "_ap", ""]
    else: RXorAP = ["users", "", ""]

    try:
        """Returns recent plays."""
        #this is probably really bad

        log.info("RecentPlay_user 함수 요청됨")
        if gamemode == 0:
            mode = "std"
            log.info(f"{RXorAP[0].upper()} 유페 STD 검사")
        elif gamemode == 1:
            mode = "taiko"
            log.info(f"{RXorAP[0].upper()} 유페 Taiko 검사")
        elif gamemode == 2:
            mode = "ctb"
            log.info(f"{RXorAP[0].upper()} 유페 CTB 검사")
        elif gamemode == 3:
            mode = "mania"
            log.info(f"{RXorAP[0].upper()} 유페 Mania 검사")
        else:
            mode = "std"
            log.error("gamemode = {}".format(gamemode))

        if text == "ORDER_Recent":
            order_by = "s.time"
        elif text == "ORDER_pp":
            order_by = "s.pp"

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
                SELECT * FROM scores{RXorAP[1]} WHERE pp >= {minpp}
            ) AS s
            LEFT JOIN users AS u ON u.id = s.userid
            LEFT JOIN (
                SELECT DISTINCT beatmap_md5, song_name, beatmap_id, beatmapset_id, ranked
                FROM beatmaps
            ) AS b ON b.beatmap_md5 = s.beatmap_md5
            WHERE s.completed != 0 and s.userid = {uid} AND s.pp >= {minpp} and s.play_mode = {gamemode}
            ORDER BY {order_by} DESC
            LIMIT 1000;
        """
        mycursor.execute(SQL)
        plays = mycursor.fetchall()
        log.info(f"DB조회 완료! | len(plays) = {len(plays)}")

        #converting the data into something readable
        ReadableArray = []
        if len(plays) is not 0:
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

                Mods = readableMods(x[7])
                if Mods == "":
                    Dicti["SongName"] = SongName

                    Dicti["beatmapID"] = x[15]
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
                
                mycursor.execute(f"SELECT COUNT(*) FROM scores{RXorAP[1]} WHERE userid = %s AND pp >= %s and play_mode = %s ORDER BY id DESC", [uid, minpp, gamemode])
                Dicti["submit_count"] = f"{mycursor.fetchone()[0]:,}"

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
                
                try:
                    Dicti["beatmapID"] = x[15]
                    if x[15] is None:
                        raise
                except:
                    log.error(x)
                    Dicti["Nodata"] += 1
                    Dicti["beatmapID"] = BeatmapMD5
                    Dicti["Nodata_SongName"] = SongName

                #유페 totalPP, accuracy, ranked_score, playcount 추가
                mycursor.execute(f"SELECT pp_{mode}, avg_accuracy_{mode}, ranked_score_{mode}, playcount_{mode} FROM {RXorAP[0]}_stats WHERE id = %s", [uid])
                stats = mycursor.fetchall()[0]

                Dicti["totalPP"] = f'{stats[0]:,}'
                Dicti["accuracy"] = round(stats[1], 2)
                Dicti["ranked_score"] = f'{stats[2]:,}'
                Dicti["playcount"] = f'{stats[3]:,}'

                ReadableArray.append(Dicti)
            
            return ReadableArray
        else:
            def NODATA(uid):
                log.error("{} 해당 유저의 {}데이터가 존재하지 않음".format(uid, RXorAP[0].upper()))

                mycursor.execute("SELECT username FROM users WHERE id = %s", [uid])
                uname = mycursor.fetchone()[0]
                ReadableArray = []
                Dicti = {}
                Dicti["Nodata"] = 0
                Dicti["SongName"] = "No {} Data on {}".format(RXorAP[1], uid)
                Dicti["Player"] = uname
                Dicti["PlayerId"] = uid
                Dicti["Score"] = None
                Dicti["pp"] = None
                Dicti["Timestamp"] = None
                Dicti["Time"] = None
                Dicti["Accuracy"] = None
                Dicti["beatmapID"] = None

                Dicti["totalPP"] = 0
                Dicti["accuracy"] = 0
                Dicti["ranked_score"] = 0
                Dicti["scoreID"] = 0
                Dicti["ranked"] = "UNKNOWN"

                Dicti["gameMode"] = " []"

                ReadableArray.append(Dicti)
                return ReadableArray
            
            return NODATA(uid)
    except:
        log.error(f"{RXorAP[0].upper()}유페 예외처리됨")
        
        return NODATA(uid)
        return "No {} Data on {}".format(RXorAP[1], uid)

@app.route("/u/vn/<uid>", methods = ["GET", "POST"])
def u_vn_bestPP(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.{ServerDomain}/u/vn/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("vn_userpage.html", data=DashData(), session=session, title="Vanilla User Page (Best pp)", config=UserConfig, StatData = RecentPlays_user("ORDER_pp", uid, int(gamemode), MinPP), MinPP = MinPP, type = "ORDER by pp")

@app.route("/u/vn/recent/<uid>", methods = ["GET", "POST"])
def u_vn_recent(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.{ServerDomain}/u/vn/recent/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("vn_userpage.html", data=DashData(), session=session, title="Vanilla UserPage (Recent)", config=UserConfig, StatData = RecentPlays_user("ORDER_Recent", uid, int(gamemode), MinPP), MinPP = MinPP, type = "ORDER by time")

@app.route("/u/rx/<uid>", methods = ["GET", "POST"])
def u_rx_bestPP(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.{ServerDomain}/u/rx/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("rx_userpage.html", data=DashData(), session=session, title="Relax User Page (Best pp)", config=UserConfig, StatData = RecentPlays_user("ORDER_pp", uid, int(gamemode), MinPP, rx=True), MinPP = MinPP, type = "ORDER by pp")

@app.route("/u/rx/recent/<uid>", methods = ["GET", "POST"])
def u_rx_recent(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.{ServerDomain}/u/rx/recent/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("rx_userpage.html", data=DashData(), session=session, title="Relax UserPage (Recent)", config=UserConfig, StatData = RecentPlays_user("ORDER_Recent", uid, int(gamemode), MinPP, rx=True), MinPP = MinPP, type = "ORDER by time")

@app.route("/u/ap/<uid>", methods = ["GET", "POST"])
def u_ap_bestPP(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.{ServerDomain}/u/ap/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("ap_userpage.html", data=DashData(), session=session, title="Autopilot User Page (Best pp)", config=UserConfig, StatData = RecentPlays_user("ORDER_pp", uid, int(gamemode), MinPP, ap=True), MinPP = MinPP, type = "ORDER by pp")

@app.route("/u/ap/recent/<uid>", methods = ["GET", "POST"])
def u_ap_recent(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.{ServerDomain}/u/ap/recent/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("ap_userpage.html", data=DashData(), session=session, title="Autopilot UserPage (Recent)", config=UserConfig, StatData = RecentPlays_user("ORDER_Recent", uid, int(gamemode), MinPP, ap=True), MinPP = MinPP, type = "ORDER by time")

@app.route("/stats", methods = ["GET", "POST"])
def StatsRoute():
    if HasPrivilege(session["AccountId"]):
        MinPP = request.form.get("minpp", 0)

        user = request.form.get("user")
        if user is not None:
            if user.isdigit():
                log.info("u/rx/recent/{} 로 리다이렉트".format(user))
                return redirect(f"/u/rx/recent/{user}")
            else:
                mycursor.execute("SELECT id FROM users WHERE username = %s", [user])
                user = mycursor.fetchone()
                user = user[0]
                log.info("u/rx/recent/{} 로 리다이렉트".format(user))
                return redirect(f"/u/rx/recent/{user}")

        return render_template("stats.html", data=DashData(), session=session, title="Server Statistics", config=UserConfig, StatData = GetStatistics(MinPP), MinPP = MinPP)
    return NoPerm(session, request.url)

#API for js
@app.route("/js/pp/<id>")
def PPApi(id):
    try:
        return jsonify({
            "pp" : str(round(CalcPP(id), 2)),
            "dtpp" : str(round(CalcPPDT(id), 2)),
            "code" : 200
        })
    except:
        return jsonify({"code" : 500})
#api mirrors
@app.route("/ping")
def Status():
    return Response(json.dumps({"code": 200}, indent=2, ensure_ascii=False), content_type='application/json')
@app.route("/js/status/api")
def ApiStatus():
    try:
        return jsonify(requests.get(UserConfig["ServerURL"] + "api/v1/ping", headers=requestHeaders, verify=False, timeout=1).json())
    except Exception as err:
        print("[ERROR] /js/status/api: ", err)
        return jsonify({
            "code" : 503
        })
@app.route("/js/status/lets")
def LetsStatus():
    try:
        return jsonify(requests.get(UserConfig["LetsAPI"] + "v1/status", headers=requestHeaders, verify=False, timeout=1).json()) #this url to provide a predictable result
    except Exception as err:
        print("[ERROR] /js/status/lets: ", err)
        return jsonify({
            "server_status" : 0
        })
@app.route("/js/status/bancho")
def BanchoStatus():
    try:
        return jsonify(requests.get(UserConfig["BanchoURL"] + "api/v1/serverStatus", headers=requestHeaders, verify=False, timeout=1).json()) #this url to provide a predictable result
    except Exception as err:
        print("[ERROR] /js/status/bancho: ", err)
        return jsonify({
            "result" : 0
        })
@app.route("/js/status/mediaserver")
def MediaserverStatus():
    try:
        return jsonify(requests.get(UserConfig["ServerURL"].replace("://", "://b.") + "status", headers=requestHeaders, verify=False, timeout=3).json()) #this url to provide a predictable result
    except Exception as err:
        print("[ERROR] /js/status/mediaserver: ", err)
        return jsonify({
            "code" : 500
        })

#actions
@app.route("/actions/wipe/<AccountID>")
def Wipe(AccountID: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 11):
        Account = GetUser(AccountID)
        WipeAccount(AccountID)
        RAPLog(session["AccountId"], f"has wiped the account {Account['Username']} ({AccountID})")
        return redirect(f"/user/edit/{AccountID}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/wipeap/<AccountID>")
def WipeAPRoute(AccountID: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 11):
        Account = GetUser(AccountID)
        WipeAutopilot(AccountID)
        RAPLog(session["AccountId"], f"has wiped the autopilot statistics for the account {Account['Username']} ({AccountID})")
        return redirect(f"/user/edit/{AccountID}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/wiperx/<AccountID>")
def WipeRXRoute(AccountID: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 11):
        Account = GetUser(AccountID)
        WipeRelax(AccountID)
        RAPLog(session["AccountId"], f"has wiped the relax statistics for the account {Account['Username']} ({AccountID})")
        return redirect(f"/user/edit/{AccountID}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/wipeva/<AccountID>")
def WipeVARoute(AccountID: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 11):
        Account = GetUser(AccountID)
        WipeVanilla(AccountID)
        RAPLog(session["AccountId"], f"has wiped the vanilla statistics for the account {Account['Username']} ({AccountID})")
        return redirect(f"/user/edit/{AccountID}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/restrict/<id>")
def Restrict(id: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 6):
        Account = GetUser(id)
        if ResUnTrict(id, request.args.get("note")):
            RAPLog(session["AccountId"], f"has restricted the account {Account['Username']} ({id})")
        else:
            RAPLog(session["AccountId"], f"has unrestricted the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/freeze/<id>")
def Freezee(id: int):
    if HasPrivilege(session["AccountId"], 6):
        Account = GetUser(id)
        FreezeHandler(id)
        RAPLog(session["AccountId"], f"has frozen the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/ban/<id>")
def Ban(id: int):
    """Do the FBI to the person."""
    if HasPrivilege(session["AccountId"], 5):
        Account = GetUser(id)
        if BanUser(id):
            RAPLog(session["AccountId"], f"has banned the account {Account['Username']} ({id})")
        else:
            RAPLog(session["AccountId"], f"has unbanned the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        return NoPerm(session, request.url)
@app.route("/actions/hwid/<id>")
def HWID(id: int):
    """Clear HWID matches."""
    if HasPrivilege(session["AccountId"], 6):
        Account = GetUser(id)
        ClearHWID(id)
        RAPLog(session["AccountId"], f"has cleared the HWID matches for the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        return NoPerm(session, request.url)
@app.route("/actions/delete/<id>")
def DeleteAcc(id: int):
    """Account goes bye bye forever."""
    if HasPrivilege(session["AccountId"], 6):
        AccountToBeDeleted = GetUser(id)
        DeleteAccount(id)
        RAPLog(session["AccountId"], f"has deleted the account {AccountToBeDeleted['Username']} ({id})")
        return redirect("/users/1")
    else:
        return NoPerm(session, request.url)
@app.route("/actions/kick/<id>")
def KickFromBancho(id: int):
    """Kick from bancho"""
    if HasPrivilege(session["AccountId"], 12):
        Account = GetUser(id)
        BanchoKick(id, "You have been kicked by an admin!")
        RAPLog(session["AccountId"], f"has kicked the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/deletebadge/<id>")
def BadgeDeath(id:int):
    if HasPrivilege(session["AccountId"], 4):
        DeleteBadge(id)
        RAPLog(session["AccountId"], f"deleted the badge with the ID of {id}")
        return redirect(url_for("Badges"))
    else:
        return NoPerm(session, request.url)

@app.route("/actions/createbadge")
def CreateBadgeAction():
    if HasPrivilege(session["AccountId"], 4):
        Badge = CreateBadge()
        RAPLog(session["AccountId"], f"Created a badge with the ID of {Badge}")
        return redirect(f"/badge/edit/{Badge}")
    else:
        return NoPerm(session, request.url)

@app.route("/actions/createprivilege")
def CreatePrivilegeAction():
    if HasPrivilege(session["AccountId"], 13):
        PrivID = CreatePrivilege()
        RAPLog(session["AccountId"], f"Created a new privilege group with the ID of {PrivID}")
        return redirect(f"/privilege/edit/{PrivID}")
    return NoPerm(session, request.url)

@app.route("/actions/deletepriv/<PrivID>")
def PrivDeath(PrivID:int):
    if HasPrivilege(session["AccountId"], 13):
        PrivData = GetPriv(PrivID)
        DelPriv(PrivID)
        RAPLog(session["AccountId"], f"deleted the privilege {PrivData['Name']} ({PrivData['Id']})")
        return redirect(url_for("EditPrivileges"))
    else:
        return NoPerm(session, request.url)


#beatmaps.rankedby 변경함수
def beatmap_rankedby(text, bm):
    if text == "BeatmapID":
        mycursor.execute("UPDATE beatmaps SET rankedby = %s WHERE beatmap_id = %s", [session["AccountId"], bm])
        mydb.commit()
        log.info("비트맵 {} rankedby 변경".format(bm))
    elif text == "BeatmapSetID":
        mycursor.execute("UPDATE beatmaps SET rankedby = %s WHERE beatmapset_id = %s", [session["AccountId"], bm])
        mydb.commit()
        log.info("비트맵 셋 {} rankedby 변경".format(bm))

#바로 아래 코드 대비한 bsid to bid
def bsid_to_bid(bsid):
    mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = %s", [bsid])
    rankedby = mycursor.fetchone()
    return rankedby[0]

#제작 포기 (pep.py에서 만들 예정)
""" @app.route("/ingame/change-bsid/<BeatmapSet>/<rankstatnum>/<uid>")
def IngameChangeRankSet(BeatmapSet: int, rankstatnum, uid):
    log.debug(f"BeatmapSet = {BeatmapSet}, rankstatnum = {rankstatnum}, uid = {uid}")
    return f"BeatmapSet = {BeatmapSet}, rankstatnum = {rankstatnum}, uid = {uid}"
    SetBMAPSetStatus(BeatmapSet, 2, session)
    RAPLog(session["AccountId"], f"ranked the beatmap set {BeatmapSet}")

    #rankedby 추가
    beatmap_rankedby("BeatmapSetID", BeatmapSet)

    return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}") """

@app.route("/action/rankset/<BeatmapSet>")
def RankSet(BeatmapSet: int):
    if HasPrivilege(session["AccountId"], 3):
        SetBMAPSetStatus(BeatmapSet, 2, session)
        RAPLog(session["AccountId"], f"ranked the beatmap set {BeatmapSet}")

        #rankedby 추가
        beatmap_rankedby("BeatmapSetID", BeatmapSet)

        return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}")
    else:
        return NoPerm(session, request.url)

#Approved 추가
@app.route("/action/approvedset/<BeatmapSet>")
def ApprovedSet(BeatmapSet: int):
    if HasPrivilege(session["AccountId"], 3):
        SetBMAPSetStatus(BeatmapSet, 3, session)
        RAPLog(session["AccountId"], f"Approved the beatmap set {BeatmapSet}")

        #rankedby 추가
        beatmap_rankedby("BeatmapSetID", BeatmapSet)

        return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}")
    else:
        return NoPerm(session, request.url)

@app.route("/action/loveset/<BeatmapSet>")
def LoveSet(BeatmapSet: int):
    if HasPrivilege(session["AccountId"], 3):
        SetBMAPSetStatus(BeatmapSet, 5, session)
        RAPLog(session["AccountId"], f"loved the beatmap set {BeatmapSet}")

        #rankedby 추가
        beatmap_rankedby("BeatmapSetID", BeatmapSet)

        return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}")
    else:
        return NoPerm(session, request.url)

#Qualified 추가
@app.route("/action/qualifiedset/<BeatmapSet>")
def QualifiedSet(BeatmapSet: int):
    if HasPrivilege(session["AccountId"], 3):
        SetBMAPSetStatus(BeatmapSet, 4, session)
        RAPLog(session["AccountId"], f"unranked the beatmap set {BeatmapSet}")

        #rankedby 추가
        beatmap_rankedby("BeatmapSetID", BeatmapSet)

        return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}")
    else:
        return NoPerm(session, request.url)

@app.route("/action/unrankset/<BeatmapSet>")
def UnrankSet(BeatmapSet: int):
    if HasPrivilege(session["AccountId"], 3):
        SetBMAPSetStatus(BeatmapSet, 0, session)
        RAPLog(session["AccountId"], f"unranked the beatmap set {BeatmapSet}")

        #rankedby 추가
        beatmap_rankedby("BeatmapSetID", BeatmapSet)

        return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}")
    else:
        return NoPerm(session, request.url)

@app.route("/action/deleterankreq/<ReqID>")
def MarkRequestAsDone(ReqID):
    if HasPrivilege(session["AccountId"], 3): DeactiveBmapReq(ReqID); return redirect("/rankreq/1")
    else: return NoPerm(session, request.url)

@app.route("/action/kickclan/<AccountID>")
def KickClanRoute(AccountID):
    if HasPrivilege(session["AccountId"], 15):
        KickFromClan(AccountID)
        return redirect("/clans/1")
    return NoPerm(session, request.url)

#error handlers
@app.errorhandler(404)
def NotFoundError(error):
    return render_template("404.html")

@app.errorhandler(500)
def BadCodeError(error):
    ConsoleLog("Misc unhandled error!", f"{error}", 3)

    #botch_sql_recovery()

    return render_template("500.html")

#we make sure session exists
@app.before_request
def BeforeRequest(): 
    if "LoggedIn" not in list(dict(session).keys()): #we checking if the session doesnt already exist
        for x in list(ServSession.keys()):
            session[x] = ServSession[x]

def NoPerm(session, redirect_url):
    """If not logged it, returns redirect to login. Else 403s. This is for convienience when page is reloaded after restart."""
    if session["LoggedIn"]:
        return render_template("403.html")
    else:
        log.chat(f"NoPerm | redirect_url = {redirect_url}")
        return redirect(f"/login?redirect_url={redirect_url}")

if __name__ == "__main__":
    Thread(target=PlayerCountCollection, args=(True,)).start()
    UpdateCachedStore()
    app.run(host= '0.0.0.0', port=UserConfig["Port"], threaded= False)
    handleUpdate() # handle update...
