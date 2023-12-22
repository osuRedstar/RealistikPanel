#This file is responsible for running the web server and (mostly nothing else)
from flask import Flask, render_template, session, redirect, url_for, request, send_from_directory, jsonify, Response
from defaults import *
from config import UserConfig
from functions import *
from colorama import Fore, init
import os
from updater import *
from threading import Thread

#log함수? 추가
from lets_common_log import logUtils as log

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

print(f" {Fore.BLUE}Running Build {GetBuild()}")
ConsoleLog(f"RealistikPanel (Build {GetBuild()}) started!")

app = Flask(__name__)
app.secret_key = os.urandom(24) #encrypts the session cookie

@app.route("/")
def home():
    redirect_url = request.args.get("redirect_url")
    if redirect_url is None:
        redirect_url = url_for("dash")

    if session["LoggedIn"]:
        return redirect(redirect_url)
    else:
        return redirect(url_for("login"))

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)
    

@app.route("/recent_RegisteredUsers")
def RecentRegisteredUsers():
    if HasPrivilege(session["AccountId"], 6):
        #Nerina
        #mycursor.execute("SELECT users.id, users.osuver, users.username, users.username_safe, users.ban_datetime FROM users WHERE current_status NOT IN ('Offline') ORDER BY {}".format(query))
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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)


@app.route("/onlineusers_list")
def OnlineUserList():
    query = request.args.get("q")
    log.debug("onlinelist query = {}".format(query))
    if query is None:
        log.debug("리다이렉트 댐")
        return redirect(f"https://admin.redstar.moe/onlineusers_list?q=id")
    #sql 인젝션 방지 (?)
    elif query != "id" and query != "username" and query != "current_status":
        log.warning("조회 되지 않는 쿼리 입력 : {}".format(query))
        return "조회 되지 않는 쿼리 입력 : {}".format(query)

    #Nerina
    mycursor.execute("SELECT id, username, current_status FROM users_stats WHERE current_status NOT IN ('Offline') ORDER BY {}".format(query));
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
            return redirect(f"https://admin.redstar.moe/restrictedusers_list?q=id")
        #sql 인젝션 방지 (?)
        elif query != "id" and query != "username" and query != "ban_datetime" and query != "privileges":
            log.warning("조회 되지 않는 쿼리 입력 : {}".format(query))
            return "조회 되지 않는 쿼리 입력 : {}".format(query)
    else:
        query = "id"
        log.info("/dash에서 /restrictedusers_list 속 함수 요청댐. 에러 방지를 위하여 쿼리 리다이렉트 비활성화 (?)")

    #Nerina
    mycursor.execute("SELECT id, username, ban_datetime, privileges FROM users WHERE ban_datetime NOT IN ('0') and privileges = 2 ORDER BY {}".format(query));
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
        log.debug("bannedlist query = {}".format(query))
        if query is None:
            log.debug("리다이렉트 댐")
            return redirect(f"https://admin.redstar.moe/bannedusers_list?q=id")
        #sql 인젝션 방지 (?)
        elif query != "id" and query != "username" and query != "ban_datetime" and query != "privileges":
            log.warning("조회 되지 않는 쿼리 입력 : {}".format(query))
            return "조회 되지 않는 쿼리 입력 : {}".format(query)
    else:
        query = "id"
        log.info("/dash에서 /bannedusers_list 속 함수 요청댐. 에러 방지를 위하여 쿼리 리다이렉트 비활성화 (?)")

    #Nerina
    mycursor.execute("SELECT id, username, ban_datetime, privileges FROM users WHERE ban_datetime NOT IN ('0') and privileges = 0 ORDER BY {}".format(query));
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
            MediaServer = requests.get("https://b.redstar.moe/status", timeout=1).json()
        except Exception as err:
            print("[ERROR] https://b.redstar.moe/status: ", err)
            MediaServer = {"code" : 503, "oszCount" : -1}
        return Response(json.dumps({"Bancho": BanchoStatus().json, "LETS": LetsStatus().json, "API": ApiStatus().json, "MediaServer": MediaServer}, indent=2, ensure_ascii=False), content_type='application/json')
    return render_template("dash.html", title="Dashboard", session=session, data=DashData(), restricteduserlist=json.loads(RestrictedUserList(dash=True))[0], banneduserlist=json.loads(BannedUserList(dash=True))[0], plays=RecentPlays(), config=UserConfig, Graph=DashActData(), MostPlayed=GetMostPlayed())

@app.route("/login", methods = ["GET", "POST"])
def login():
    redirect_url = request.args.get("redirect_url")
    if redirect_url is None:
        redirect_url = url_for("home")
    else:
        redirect_url = f"https://admin.redstar.moe/?redirect_url={redirect_url}"

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
    else:
        return redirect(url_for("dash"))

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
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
    else:
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
        else:
            channel = request.form['channel']
            msg = request.form['message']

            #Ingame #announce추가
            params = {"k": UserConfig['FokaKey'], "to": channel, "msg": msg}
            FokaMessage(params)

            log.info("FokaMessage sent")
            log.info("To: {}".format(channel))
            log.info("Message: {}".format(msg))

            return render_template("fokamessage.html", title="Fokamessage", data=DashData(), session=session, config=UserConfig, success=f"Successfully Send FokaMessage! \n{msg}")
            #return redirect(f"/fokamessage") #does this even work

@app.route("/iptousers", methods = ["GET", "POST"])
def ipToUser():
    if request.method == "GET":
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
        else:
            return render_template("iptousers.html", title="IP To users", data=DashData(), session=session, config=UserConfig)
    else:
        ip = request.form['IP']
        mycursor.execute(f"SELECT userid, username FROM ip_user INNER JOIN users ON ip_user.userid = users.id WHERE ip = '{ip}'")
        result = [{"userID": i[0], "username": i[1]} for i in mycursor.fetchall()]
        return Response(json.dumps({"ip": ip, "userinfo": result}, indent=2, ensure_ascii=False), content_type='application/json')
@app.route("/iptousers/<ip>")
def ipToUserApi(ip):
    if not HasPrivilege(session["AccountId"]): #mixing things up eh
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)
    else:
        mycursor.execute(f"SELECT userid, username FROM ip_user INNER JOIN users ON ip_user.userid = users.id WHERE ip = '{ip}'")
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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

""" RX 리더보드 """
@app.route("/frontend/leaderboard/rx")
#아 국가별 리더보드 만들기 존나 귀찮다
def RX_leaderboard():
    query = request.args.get("mode")
    query2 = request.args.get("board")
    if query is None:
        return redirect(f"https://admin.redstar.moe/frontend/leaderboard/rx?mode=0&board=0")
    elif query2 is None:
         return redirect(f"https://admin.redstar.moe/frontend/leaderboard/rx?mode=0&board=0")
    elif int(query) > 3:
        return "WHAT IS THAT MODE?"

    mode = ["std", "taiko", "ctb", "mania"]
    mode = mode[int(query)]

    if int(query2) == 0:
        mycursor.execute(f"SELECT rx_stats.country, rx_stats.id, rx_stats.username, rx_stats.pp_{mode}, rx_stats.ranked_score_{mode}, rx_stats.avg_accuracy_{mode}, rx_stats.playcount_{mode}, rx_stats.level_{mode} FROM rx_stats LEFT JOIN users ON users.id = rx_stats.id WHERE users.privileges NOT IN (0) AND users.privileges NOT IN (2) ORDER BY case when pp_{mode} then pp_{mode} END DESC, case when pp_{mode} = 0 then ranked_score_{mode} END DESC")
        log.info("rx 리더보드 pp 정렬")
    elif int(query2) == 1:
        mycursor.execute(f"SELECT rx_stats.country, rx_stats.id, rx_stats.username, rx_stats.pp_{mode}, rx_stats.ranked_score_{mode}, rx_stats.avg_accuracy_{mode}, rx_stats.playcount_{mode}, rx_stats.level_{mode} FROM rx_stats LEFT JOIN users ON users.id = rx_stats.id WHERE users.privileges NOT IN (0) AND users.privileges NOT IN (2) ORDER BY case when ranked_score_{mode} then ranked_score_{mode} END DESC, case when ranked_score_{mode} = 0 then pp_{mode} END DESC")
        log.info("rx 리더보드 score 정렬")
    rx_lb = mycursor.fetchall()

    ReadableArray = []
    if len(rx_lb) is not 0:
        i = 1
        for x in rx_lb:
            Dicti = {}
            Dicti["Rank"] = i

            Dicti["Country"] = x[0]
            Dicti["PlayerId"] = x[1]
            Dicti["Player"] = x[2]

            Dicti["pp"] = f"{round(x[3], 2):,}"
            Dicti["Score"] = f'{x[4]:,}'

            Dicti["Accuracy"] = f"{round(x[5], 2):,}"

            Dicti["Playcount"] = f"{x[6]:,}"
            Dicti["Level"] = f"{x[7]}"

            ReadableArray.append(Dicti)
            i += 1
    
    return render_template("rx_leaderboard.html", data=DashData(), session=session, title="Relax Leaderboard", config=UserConfig, StatData = ReadableArray, type = f"ORDER by pp_{mode}")

""" give-betatag http """
@app.route("/frontend/give-betatag/<id>")
def give_betatag(id):
    mycursor.execute("SELECT username FROM users WHERE id = {}".format(id))
    username = mycursor.fetchone()[0]

    mycursor.execute("SELECT id FROM badges WHERE name = 'Beta Tester'")
    beta_badge_id = mycursor.fetchone()[0]

    try:
        mycursor.execute("SELECT id, user, badge FROM user_badges WHERE user = {} AND badge = {}".format(id, beta_badge_id))
        have_beta_badge = mycursor.fetchall()[0]
        msg = f"Refused | {username} ({id}) already have Beta Tester ({beta_badge_id}) badge"
        log.warning(msg)
        return msg
    except:
        mycursor.execute("INSERT INTO user_badges (user, badge) VALUES (%s, %s)", (id, beta_badge_id,))
        mydb.commit()
    
    msg = f"Success | {username} ({id}) given Beta Tester ({beta_badge_id})"
    log.debug(msg)
    return msg

""" rankedby http """
@app.route("/frontend/rankedby/<id>")
def ranked_by(id):
    mycursor.execute("SELECT rankedby FROM beatmaps WHERE beatmap_id = {}".format(id))
    try:
        rankedby = mycursor.fetchone()[0]
    except:
        log.error(f"{id} rankedby 조회 실패!")
        rankedby = ""
    return rankedby

""" ranked_status http """
@app.route("/frontend/ranked_status/<id>")
def ranked_status(id):
    mycursor.execute("SELECT ranked FROM beatmaps WHERE beatmap_id = {}".format(id))
    try:
        ranked = mycursor.fetchone()[0]
    except:
        log.error(f"{id} ranked_status 조회 실패!")
        return '["", ""]'

    if ranked == 2:
        return f'["Ranked", 2]'
        #return "Ranked"
    elif ranked == 5:
        return f'["Loved", 5]'
        #return "Loved"
    elif ranked == 3:
        return f'["Approved", 3]'
        #return "Approved"
    elif ranked == 4:
        return f'["Qualified", 4]'
        #return "Qualified"
    elif ranked == 0:
        return f'["Unranked", 0]'
        #return "Unranked"

#/rank/<id> 요청시 id가 bid, bsid 둘다 DB에 존재할경우 선택 페이지
@app.route("/rank/select/<id>")
def RankMap_select(id):
    log.debug("/ranked/select/<id> 요청 완료")
    mycursor.execute("SELECT rankedby FROM beatmaps WHERE beatmap_id = {}".format(id))
    rankedby = mycursor.fetchone()
    
    return render_template("search_beatmap.html", title="Searched Beatmap!", data=DashData(), session=session, config=UserConfig, song_query = id, SuggestedBmaps2 = SplitList(SearchBeatmap(id, rank_select = True)))
    #return render_template("beatrank_select.html", title="Select Beatmap!", data=DashData(), session=session, beatdata=SplitList(GetBmapInfo(id)), config=UserConfig, Id= id)

@app.route("/rank/<id>", methods = ["GET", "POST"])
def RankMap(id):
    #비트맵셋 요청시 리다이렉트
    mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = {}".format(id))
    check_beatmapSet = mycursor.fetchone()

    #비트맵셋 요청시 리다이렉트 --> 혹시나 DB중복감지
    mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmap_id = {}".format(id))
    check_beatmap = mycursor.fetchone()

    if check_beatmapSet is not None and check_beatmap is not None:
        log.debug("{} 는 비트맵셋, 비트맵 둘다 존재함".format(id))
        log.debug("비트맵 선택 페이지 리다이렉트")
        return redirect(f"/rank/select/{id}")

    #비트맵셋 요청시 리다이렉트
    if check_beatmapSet is not None:
        log.warning("/rank/{} 에서 비트맵셋 감지.".format(id))
        log.warning("/rank/{} 로 리다이렉트.".format(check_beatmapSet[0]))
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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/rank", methods = ["GET", "POST"])
def RankFrom():
    if request.method == "GET":
        if HasPrivilege(session["AccountId"], 3):
            return render_template("rankform.html", title="Rank a beatmap!", data=DashData(), session=session, config=UserConfig, SuggestedBmaps = SplitList(GetSuggestedRank()))
        else:
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
    else:
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
        else:
            return redirect(f"/rank/{request.form['bmapid']}") #does this even work



from discord_webhook import DiscordWebhook, DiscordEmbed
@app.route("/frontend/rank_request/set_qualified/<type>/<bid>")
def frontend_rankRequest_setQualified(type, bid):
    first_bid = bid
    BeatmapSet = 0
    log.info("홈페이지에서 리퀘 도착")
    try:
        if type == "b":
            log.info("비트맵 아이디 감지 {}".format(bid))
            #비트맵셋 아이디 요청
            #param = {'k': '4597ac5b5d5f0b3dace4103c6ae0f9a69fccce6b', 'b': first_bid}
            param = {'k': UserConfig["APIKey"], 'b': first_bid}
            r = requests.get('https://osu.ppy.sh/api/get_beatmaps', params=param)
            r = r.json()

            BeatmapSet = r[0]["beatmapset_id"]
            bid = r[0]["beatmapset_id"]
            
            #param = {'k': '4597ac5b5d5f0b3dace4103c6ae0f9a69fccce6b', 's': bid}
            param = {'k': UserConfig["APIKey"], 's': bid}
            r = requests.get('https://osu.ppy.sh/api/get_beatmaps', params=param)
            r = r.json()

            #DB등록작업
            for i in r:
                bid = i["beatmap_id"]
                param = {'b': bid}
                requests.get('https://old.redstar.moe/letsapi/v1/pp', params=param)
                log.info("{} 비트맵 DB에 저장중".format(bid))

        elif type == "s":
            log.info("비트맵셋 아이디 감지 {}".format(bid))
            BeatmapSet = bid
            #param = {'k': '4597ac5b5d5f0b3dace4103c6ae0f9a69fccce6b', 's': bid}
            param = {'k': UserConfig["APIKey"], 's': bid}
            r = requests.get('https://osu.ppy.sh/api/get_beatmaps', params=param)
            r = r.json()

            #DB등록작업
            for i in r:
                bid = i["beatmap_id"]
                param = {'b': bid}
                requests.get('https://old.redstar.moe/letsapi/v1/pp', params=param)
                log.info("{} 비트맵 DB에 저장중".format(bid))
    except:
        log.error("ERROR: 반초 요청 + Redstar DB등록 작업 실패")
        return "ERROR: 반초 요청 + Redstar DB등록 작업 실패"

    try:
        if type == "b":
            mycursor.execute("SELECT ranked, ranked_status_freezed FROM beatmaps WHERE beatmap_id = %s", (first_bid,))
            is_requested = mycursor.fetchall()
            log.debug("is_requested = {}".format(is_requested))
        elif type == "s":
            mycursor.execute("SELECT ranked, ranked_status_freezed FROM beatmaps WHERE beatmapset_id = %s", (first_bid,))
            is_requested = mycursor.fetchall()
            log.debug("is_requested = {}".format(is_requested))

        if is_requested[0][0] is not 0 and is_requested[0][1] is not 0:
            log.warning("{}/{} 값이 리퀘스트에 존재함?".format(type, first_bid))
            log.info("작업중지함")
            return "{}/{} 값이 리퀘스트에 존재함?, 작업중지함".format(type, first_bid)
        else:
            log.info("{}/{} 값이 리퀘스트에 존재하지 않음?".format(type, first_bid))
            log.info("다음 작업으로 넘어감")
    except:
        log.error("ERROR: 리퀘여부 확인 작업 실패")
        return "ERROR: 리퀘여부 확인 작업 실패"

    try:
        mycursor.execute("SELECT userid FROM rank_requests WHERE bid = %s AND type = %s", (first_bid, type))
        requestby_id = mycursor.fetchone()[0]

        mycursor.execute("SELECT username FROM users WHERE id = %s", (requestby_id,))
        requestby_username = mycursor.fetchone()[0]

        #에러나서 type s 추가
        if type == "b":
            mycursor.execute("SELECT ranked FROM beatmaps WHERE beatmap_id = %s", (first_bid,))
            is_unranked = mycursor.fetchone()[0]
        elif type == "s":
            mycursor.execute("SELECT ranked FROM beatmaps WHERE beatmap_id = %s", (bid,))
            is_unranked = mycursor.fetchone()[0]

        if is_unranked == 0:
            #퀄파로 변경
            mycursor.execute("UPDATE beatmaps SET rankedby = 999, ranked = 4, ranked_status_freezed = 1 WHERE beatmapset_id = %s", (BeatmapSet,))
            mydb.commit()
            log.info("리퀘 비트맵셋 {} 퀄파 변경".format(BeatmapSet))
        elif is_unranked == 5:
            log.warning("럽드 확인함")
            mycursor.execute("UPDATE beatmaps SET ranked_status_freezed = 1 WHERE beatmapset_id = %s", (BeatmapSet,))
            mydb.commit()
            log.info("럽드 ranked_status_freezed 1로 변경")

        else:
            log.warning("퀄파로 변경중 언랭크가 아닌 값을 발견함")
    except:
        log.error("ERROR: 리퀘요청자 가져오기 + 퀄파 변경 작업 실패")
        log.debug("requestby_id = {}".format(requestby_id))
        log.debug("requestby_username = {}".format(requestby_username))
        log.debug("is_unranked = {}".format(is_unranked))
        
        return "ERROR: 리퀘요청자 가져오기 + 퀄파 변경록 작업 실패"

    try:
        mycursor.execute("SELECT song_name, beatmap_id FROM beatmaps WHERE beatmapset_id = %s LIMIT 1", (BeatmapSet,))
        MapData = mycursor.fetchone()
        #Getting bmap name without diff
        BmapName = MapData[0].split("[")[0].rstrip() #¯\_(ツ)_/¯ might work
        
        URL = "https://discord.com/api/webhooks/1076661302979739678/5e7n8ZJSjPHlzFVjvVdu4Fi2LuxgKVz6mYtVwlasGjYHuelOLVLhSredSxim6246vADH"
        webhook = DiscordWebhook(url=URL)
        embed = DiscordEmbed(description=f"Status Changed by Devlant. <@&904084069413965944>\nRequested by {requestby_username} ({requestby_id})", color=242424) #this is giving me discord.py vibes
        embed.set_author(name=f"{BmapName} was just Qualified. (Beatmap_Set)", url=f"https://admin.redstar.moe/rank/{MapData[1]}", icon_url=f"https://a.redstar.moe/999") #will rank to random diff but yea
        #embed.set_author(name=f"{mapa[0]} was just Qualified (Beatmap_Set)", url=f"{UserConfig['ServerURL']}b/{bid}", icon_url=f"{UserConfig['AvatarServer']}{999}")
        embed.set_footer(text="via RealistikPanel! With Frontend")
        #embed.set_image(url=f"https://subapi.nerinyan.moe/bg/-{BeatmapSet}")
        embed.set_image(url=f"https://b.redstar.moe/bg/{first_bid}")
        webhook.add_embed(embed)
        print(" * Posting webhook!")
        webhook.execute()


        ingamemsg = f"[{UserConfig['ServerURL']}u/999 Devlant] Qualified the map_set [https://osu.redstar.moe/s/{BeatmapSet} {BmapName}]  [osu://dl/{BeatmapSet} osu!direct]"
        params = {"k": UserConfig['FokaKey'], "to": "#ranked", "msg": ingamemsg}
        FokaMessage(params)
        log.chat("1차 인게임 공지 전송 완료")

        ingamemsg = f"Requested Beatmap By [{UserConfig['ServerURL']}u/{requestby_id} {requestby_username}] ({requestby_id})"
        params = {"k": UserConfig['FokaKey'], "to": "#ranked", "msg": ingamemsg}
        FokaMessage(params)
        log.chat("2차 인게임 공지 전송 완료")

        return "{} 비트맵셋 퀄파로 변경 완료".format(BeatmapSet)
    except:
        log.error("ERROR: 디코 웹훅 + 인게임 알림 작업 실패")
        return "ERROR: 디코 웹훅 + 인게임 알림 작업 실패"

#/rank/search 추가
import requests
def SearchBeatmap(song_query, rank_select = False):
    log.debug("/rank/<id>에서 DB에 bid, bsid 둘다 존재할 겅우, rank_select = {}".format(rank_select))
    #/rank/<id>에서 DB에 bid, bsid 둘다 존재할 겅우
    if rank_select:
        Beatmaps = [0, 0]

        #bid
        mycursor.execute("SELECT beatmapset_id FROM beatmaps WHERE beatmap_id = {}".format(song_query))
        bsid = mycursor.fetchone()[0]
        mycursor.execute("SELECT beatmap_id, song_name, beatmapset_id, rankedby FROM beatmaps WHERE beatmapset_id = {}".format(bsid))
        a = mycursor.fetchall()[0]
        Beatmaps[0] = a

        #bsid
        mycursor.execute("SELECT beatmap_id, song_name, beatmapset_id, rankedby FROM beatmaps WHERE beatmapset_id = {}".format(song_query))
        a2 = mycursor.fetchall()[0]
        Beatmaps[1] = a2
    else:
        #기존 곡 서치 (비트맵 이름)
        mycursor.execute(f"SELECT beatmap_id, song_name, beatmapset_id, rankedby FROM beatmaps WHERE song_name LIKE '%{song_query}%' GROUP BY beatmapset_id")
        Beatmaps = mycursor.fetchall()

    BeatmapList = []

    for TopBeatmap in Beatmaps:

        r = requests.get(f'https://cheesegull.redstar.moe/api/s/{TopBeatmap[2]}')
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
            "Cover" : f"https://b.redstar.moe/bg/{TopBeatmap[0]}",
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
    mycursor.execute(f"SELECT username FROM users WHERE id = {id}")
    username = mycursor.fetchone()[0]

    mycursor.execute(f"SELECT id, k, u, t FROM password_recovery WHERE u = '{username}' AND k LIKE 'Realistik Panel : %' ORDER BY id DESC LIMIT 1")
    info = mycursor.fetchone()
    if info is None:
        noRecoveryData = True
    else:
        noRecoveryData = False
        exfireDate = int(info[3].timestamp()) + 300
        nowDate = time.time()
        key = info[1].replace("Realistik Panel : ", "")
        
        if exfireDate < nowDate:
            noRecoveryData = True
            mycursor.execute(f"DELETE FROM password_recovery WHERE u = '{username}' AND k LIKE 'Realistik Panel : %' ORDER BY id DESC LIMIT 1")
            mydb.commit()

            log.warning("비번 재설정 키 만료됨!")
            html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Password Changed!</title>
                    <meta http-equiv="refresh" content="3;url=https://admin.redstar.moe/frontend/pwreset/{id}">
                </head>
                <body>
                    <h1 style="text-align: center;">Key Exfired! Redirect pwreset page after 3sec</h1>
                </body>
                </html>
            """

            return html

    if request.method == "GET":
        if noRecoveryData:
            mycursor.execute(f"SELECT email FROM users WHERE id = {id}")
            email = mycursor.fetchone()[0]

            code = sendPwresetMail(id, email)

            return render_template("pwreset_confirm.html", title="Verifying!", data=DashData(), session=session, success="Check Your Email!", config=UserConfig, code=code, password=None, pw=False)
        else:
            return render_template("pwreset_confirm.html", title="Verifying! 22", data=DashData(), session=session, success="Check Your Email! 22", config=UserConfig, code=key, password=None, pw=False)
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

            mycursor.execute(f"DELETE FROM password_recovery WHERE u = '{username}' AND k LIKE 'Realistik Panel : %' ORDER BY id DESC LIMIT 1")
            mydb.commit()

            html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Password Changed!</title>
                    <meta http-equiv="refresh" content="3;url=https://redstar.moe/login">
                </head>
                <body>
                    <h1 style="text-align: center;">password changed!! Redirect login page after 3sec</h1>
                </body>
                </html>
            """

            return html
            return render_template("pwreset_confirm.html", title="Password Changed!", data=DashData(), session=session, success="Password Changed!", config=UserConfig, code = code, password = password, pw = True) 
        except:
            password = None

        if code == key:
            if exfireDate > nowDate: 
                return render_template("pwreset_confirm.html", title="Reset Password!", data=DashData(), session=session, config=UserConfig, code = code, password = password, pw = True)
            else:
                log.warning("비번 재설정 키 만료됨!")
                mycursor.execute(f"DELETE FROM password_recovery WHERE id = {info[0]} AND k LIKE 'Realistik Panel : %'")
                mydb.commit()

                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Password Changed!</title>
                    <meta http-equiv="refresh" content="3;url=https://admin.redstar.moe/frontend/pwreset/{id}">
                </head>
                <body>
                    <h1 style="text-align: center;">Key Exfired! Redirect pwreset page after 3sec</h1>
                </body>
                </html>
            """

            return html
        else:
            return render_template("pwreset_confirm.html", title="Wrong Key!", data=DashData(), session=session, error="Wrong Key!", config=UserConfig, code = code, password = None, pw = False)

""" pwreset http """
@app.route("/frontend/pwreset", methods = ["GET", "POST"])
def get_pw_reset():
    if request.method == "POST":
        userinfo = request.form["userinfo"]
        try:
            #ID인 경우
            userID = int(userinfo)
        except:
            log.error(f"userinfo 는 숫자가 아님 | {userinfo}")

            #username, email인 경우
            userID = FindUserByUsername(userinfo, 1)
            if len(userID) == 0:
                log.error(f"user Not Found! | {userinfo}")
                return f"user Not Found! | {userinfo}"
            userID = userID[0]["Id"]

        return redirect(f"/frontend/pwreset/{userID}") #does this even work
    else:
        return render_template("pwreset.html", title="Reset Password!", data=DashData(), session=session, config=UserConfig)

@app.route("/rank/search/<song_query>")
def SearchMap(song_query):
    if HasPrivilege(session["AccountId"], 3):

        log.info("{} 검색중".format(song_query))

        return render_template("search_beatmap.html", title="Searched Beatmap!", data=DashData(), session=session, config=UserConfig, song_query = song_query, SuggestedBmaps2 = SplitList(SearchBeatmap(song_query)))
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/rank/search", methods = ["GET", "POST"])
def SearchMap_Post():
    if request.method == "POST":
        if not HasPrivilege(session["AccountId"]): #mixing things up eh
                redirect_url = request.url.replace("http", "https")
                return NoPerm(session, redirect_url)
        else:
            return redirect(f"/rank/search/{request.form['songname']}") #does this even work
    else:
        return redirect(f"/rank")
    
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

    mycursor.execute(f"SELECT email FROM users WHERE id = {userID}")
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
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
    else:
        if HasPrivilege(session["AccountId"]):
            userID = request.form["userid"]
            mycursor.execute(f"SELECT email FROM users WHERE id = {userID}")
            email = mycursor.fetchone()[0]
            beatmapInfo = {"bid": request.form["bid"], "beatmapInfo": request.form["msg"]}
            sendBanMail(session, userID, email, beatmapInfo)
            return render_template("sendbanmail.html", title="Send Ban Mail", data=DashData(), session=session, config=UserConfig, success=f"Successfully Send Ban mail! to {email}")
        else:
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)

@app.route("/sendemail", methods = ["GET", "POST"])
def send_mail():
    if request.method == "GET":
        if HasPrivilege(session["AccountId"]):
            return render_template("sendemail.html", title="Send Email", data=DashData(), session=session, config=UserConfig)
        else:   
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
    else:
        if HasPrivilege(session["AccountId"]):
            email = request.form["email"]
            subject = request.form["subject"]
            msg = request.form["msg"]
            sendEmail(session, email, subject, msg)
            return render_template("sendemail.html", title="Send Email", data=DashData(), session=session, config=UserConfig, success=f"Successfully Send Email! to {email}")
        else:
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)


@app.route("/users/<page>", methods = ["GET", "POST"])
def Users(page = 1):
    if HasPrivilege(session["AccountId"], 6):
        if request.method == "GET":
            return render_template("users.html", title="Users", data=DashData(), session=session, config=UserConfig, UserData = FetchUsers(int(page)-1), page=int(page), Pages=UserPageCount())
        if request.method == "POST":
            return render_template("users.html", title="Users", data=DashData(), session=session, config=UserConfig, UserData = FindUserByUsername(request.form["user"], int(page)), page=int(page), User=request.form["user"], Pages=UserPageCount())
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)

@app.route("/user/edit/<id>", methods = ["GET", "POST"])
def EditUser(id):
    def client_ver():
        mycursor.execute("SELECT osuver FROM users WHERE id = %s", (id,))
        return mycursor.fetchone()[0]
    def hw_user_info():
        mycursor.execute("SELECT * FROM hw_user WHERE userid = %s", (id,))
        return mycursor.fetchone()

    if request.method == "GET":
        if HasPrivilege(session["AccountId"], 6):
            return render_template("edituser.html", data=DashData(), session=session, title="Edit User", config=UserConfig, uid=id, osuver=client_ver(), hw_user_info=hw_user_info(), UserData=UserData(id), Privs = GetPrivileges(), UserBadges= GetUserBadges(id), badges=GetBadges(), ShowIPs = HasPrivilege(session["AccountId"], 16))
        else:
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)
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
            redirect_url = request.url.replace("http", "https")
            return NoPerm(session, redirect_url)


@app.route("/logs/<page>")
def Logs(page):
    if HasPrivilege(session["AccountId"], 7):
        return render_template("raplogs.html", data=DashData(), session=session, title="Logs", config=UserConfig, Logs = RAPFetch(page), page=int(page), Pages = RapLogCount())
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/action/confirm/delete/<id>")
def ConfirmDelete(id):
    """Confirms deletion of acc so accidents dont happen"""
    #i almost deleted my own acc lmao
    #me forgetting to commit changes saved me
    if HasPrivilege(session["AccountId"], 6):
        AccountToBeDeleted = GetUser(id)
        return render_template("confirm.html", data=DashData(), session=session, title="Confirmation Required", config=UserConfig, action=f"delete the user {AccountToBeDeleted['Username']}", yeslink=f"/actions/delete/{id}", backlink=f"/user/edit/{id}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/user/iplookup/<ip>")
def IPUsers(ip):
    if HasPrivilege(session["AccountId"], 16):
        IPUserLookup  = FindWithIp(ip)
        UserLen = len(IPUserLookup)
        return render_template("iplookup.html", data=DashData(), session=session, title="IP Lookup", config=UserConfig, ipusers=IPUserLookup, IPLen = UserLen, ip=ip)
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/badges")
def Badges():
    if HasPrivilege(session["AccountId"], 4):
        return render_template("badges.html", data=DashData(), session=session, title="Badges", config=UserConfig, badges=GetBadges())
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/privileges")
def EditPrivileges():
    if HasPrivilege(session["AccountId"], 13):
        return render_template("privileges.html", data=DashData(), session=session, title="Privileges", config=UserConfig, privileges=GetPrivileges())
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/console")
def Console():
    if HasPrivilege(session["AccountId"], 14):
        return render_template("consolelogs.html", data=DashData(), session=session, title="Console Logs", config=UserConfig, logs=GetLog())
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/changelogs")
def ChangeLogs():
    if HasPrivilege(session["AccountId"]):
        return render_template("changelog.html", data=DashData(), session=session, title="Change Logs", config=UserConfig, logs=Changelogs)
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)


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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/donorremove/<AccountID>")
def RemoveDonorRoute(AccountID):
    if HasPrivilege(session["AccountId"], 6):
        RemoveSupporter(AccountID, session)
        return redirect(f"/user/edit/{AccountID}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)


@app.route("/rankreq/<Page>")
def RankReq(Page):
    if HasPrivilege(session["AccountId"], 3):
        return render_template("rankreq.html", data=DashData(), session=session, title="Ranking Requests", config=UserConfig, RankRequests = GetRankRequests(int(Page)), page = int(Page))
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/clans/<Page>")
def ClanRoute(Page):
    if HasPrivilege(session["AccountId"], 15):
        return render_template("clansview.html", data=DashData(), session=session, title="Clans", config=UserConfig, page = int(Page), Clans = GetClans(Page), Pages = GetClanPages())
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/clan/<ClanID>", methods = ["GET", "POST"])
def ClanEditRoute(ClanID):
    if HasPrivilege(session["AccountId"], 15):
        if request.method == "GET":
            return render_template("editclan.html", data=DashData(), session=session, title="Clans", config=UserConfig, Clan=GetClan(ClanID), Members=SplitList(GetClanMembers(ClanID)), ClanOwner = GetClanOwner(ClanID))
        ApplyClanEdit(request.form, session)
        return render_template("editclan.html", data=DashData(), session=session, title="Clans", config=UserConfig, Clan=GetClan(ClanID), Members=SplitList(GetClanMembers(ClanID)), ClanOwner = GetClanOwner(ClanID), success="Clan edited successfully!")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/clan/delete/<ClanID>")
def ClanFinalDelete(ClanID):
    if HasPrivilege(session["AccountId"], 15):
        NukeClan(ClanID, session)
        return redirect("/clans/1")
    redirect_url = request.url.replace("http", "https")
    return NoPerm(session, redirect_url)

@app.route("/clan/confirmdelete/<ClanID>")
def ClanDeleteConfirm(ClanID):
    if HasPrivilege(session["AccountId"], 15):
        Clan = GetClan(ClanID)
        return render_template("confirm.html", data=DashData(), session=session, title="Confirmation Required", config=UserConfig, action=f" delete the clan {Clan['Name']}", yeslink=f"/clan/delete/{ClanID}", backlink="/clans/1")
    redirect_url = request.url.replace("http", "https")
    return NoPerm(session, redirect_url)



#릴렉 유저별 최근 기록 조회
def RecentPlays_user_rx(text, uid, gamemode = 0, minpp = 0):
    try:
        """Returns recent plays."""
        #this is probably really bad

        log.info("RecentPlay_user 함수 요청됨")
        if gamemode == 0:
            log.info("rx유페 STD 검사")
        elif gamemode == 1:
            log.info("rx유페 Taiko 검사")
        elif gamemode == 2:
            log.info("rx유페 CTB 검사")
        elif gamemode == 3:
            log.info("rx유페 Mania 검사")
        else:
            log.error("gamemode = {}".format(gamemode))

        if text == "ORDER_Recent":
            order_by = "s.time"
        elif text == "ORDER_pp":
            order_by = "s.pp"

        #rx
        #mycursor.execute(f"SELECT scores_relax.beatmap_md5, users.username, scores_relax.userid, scores_relax.time, scores_relax.score, scores_relax.pp, scores_relax.play_mode, scores_relax.mods, scores_relax.300_count, scores_relax.100_count, scores_relax.50_count, scores_relax.misses_count, scores_relax.id, scores_relax.completed FROM scores_relax LEFT JOIN users ON users.id = scores_relax.userid WHERE scores_relax.completed != 0 and scores_relax.userid = {uid} AND scores_relax.pp >= {minpp} and scores_relax.play_mode = {gamemode} ORDER BY {order_by} DESC limit 100")
        
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
                SELECT * FROM scores_relax WHERE pp >= {minpp}
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

                Mods = ModToText(x[7])
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
                
                mycursor.execute("SELECT COUNT(*) FROM scores_relax WHERE userid = %s AND scores_relax.pp >= %s and scores_relax.play_mode = %s ORDER BY id DESC", (uid, minpp, gamemode))
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

                #유페 totalPP, ranked_score추가
                if gamemode == 0:
                    mycursor.execute("SELECT pp_std, avg_accuracy_std, ranked_score_std FROM rx_stats WHERE id = %s", (uid,))
                    result = mycursor.fetchall()[0]
                    totalPP = result[0]
                    accuracy = result[1]
                    ranked_score = result[2]
                    Dicti["gameMode"] = " [STD]"
                elif gamemode == 1:
                    mycursor.execute("SELECT pp_taiko, avg_accuracy_taiko, ranked_score_taiko FROM rx_stats WHERE id = %s", (uid,))
                    result = mycursor.fetchall()[0]
                    totalPP = result[0]
                    accuracy = result[1]
                    ranked_score = result[2]
                    Dicti["gameMode"] = " [Taiko]"
                elif gamemode == 2:
                    mycursor.execute("SELECT pp_ctb, avg_accuracy_ctb, ranked_score_ctb FROM rx_stats WHERE id = %s", (uid,))
                    result = mycursor.fetchall()[0]
                    totalPP = result[0]
                    accuracy = result[1]
                    ranked_score = result[2]
                    Dicti["gameMode"] = " [CTB]"
                elif gamemode == 3:
                    mycursor.execute("SELECT pp_mania, avg_accuracy_mania, ranked_score_mania FROM rx_stats WHERE id = %s", (uid,))
                    result = mycursor.fetchall()[0]
                    totalPP = result[0]
                    accuracy = result[1]
                    ranked_score = result[2]
                    Dicti["gameMode"] = " [Mania]"
                else:
                    mycursor.execute("SELECT pp_std, avg_accuracy_std, ranked_score_std FROM rx_stats WHERE id = %s", (uid,))
                    result = mycursor.fetchall()[0]
                    totalPP = result[0]
                    accuracy = result[1]
                    ranked_score = result[2]
                    Dicti["gameMode"] = " []"

                Dicti["totalPP"] = f"{totalPP:,}"
                Dicti["accuracy"] = round(accuracy, 2)
                Dicti["ranked_score"] = f"{ranked_score:,}"

                ReadableArray.append(Dicti)
            
            return ReadableArray
        else:
            def NODATA(uid):
                log.error("{} 해당 유저의 rx데이터가 존재하지 않음".format(uid))

                mycursor.execute("SELECT username FROM users WHERE id = %s", (uid,))
                uname = mycursor.fetchone()[0]
                ReadableArray = []
                Dicti = {}
                Dicti["Nodata"] = 0
                Dicti["SongName"] = "No Relax Data on {}".format(uid)
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
        log.error("rx유페 예외처리됨")
        
        return NODATA(uid)
        return "No Relax Data on {}".format(uid)

@app.route("/u/rx/<uid>", methods = ["GET", "POST"])
def u_rx_bestPP(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.redstar.moe/u/rx/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("rx_userpage.html", data=DashData(), session=session, title="Relax User Page (Best pp)", config=UserConfig, StatData = RecentPlays_user_rx("ORDER_pp", uid, int(gamemode), MinPP), MinPP = MinPP, type = "ORDER by pp")

@app.route("/u/rx/recent/<uid>", methods = ["GET", "POST"])
def u_rx_recent(uid):
    gamemode = request.args.get("mode")
    if gamemode is None:
        return redirect(f"https://admin.redstar.moe/u/rx/recent/{uid}?mode=0")
    MinPP = request.form.get("minpp", 0)
    return render_template("rx_userpage.html", data=DashData(), session=session, title="Relax UserPage (Recent)", config=UserConfig, StatData = RecentPlays_user_rx("ORDER_Recent", uid, int(gamemode), MinPP), MinPP = MinPP, type = "ORDER by time")


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
                mycursor.execute("SELECT id FROM users WHERE username = %s", (user,))
                user = mycursor.fetchone()
                user = user[0]
                log.info("u/rx/recent/{} 로 리다이렉트".format(user))
                return redirect(f"/u/rx/recent/{user}")

        return render_template("stats.html", data=DashData(), session=session, title="Server Statistics", config=UserConfig, StatData = GetStatistics(MinPP), MinPP = MinPP)
    redirect_url = request.url.replace("http", "https")
    return NoPerm(session, redirect_url)

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
@app.route("/js/status/api")
def ApiStatus():
    try:
        return jsonify(requests.get(UserConfig["ServerURL"] + "api/v1/ping", verify=False, timeout=1).json())
    except Exception as err:
        print("[ERROR] /js/status/api: ", err)
        return jsonify({
            "code" : 503
        })
@app.route("/js/status/lets")
def LetsStatus():
    try:
        return jsonify(requests.get(UserConfig["LetsAPI"] + "v1/status", verify=False, timeout=1).json()) #this url to provide a predictable result
    except Exception as err:
        print("[ERROR] /js/status/lets: ", err)
        return jsonify({
            "server_status" : 0
        })
@app.route("/js/status/bancho")
def BanchoStatus():
    try:
        return jsonify(requests.get(UserConfig["BanchoURL"] + "api/v1/serverStatus", verify=False, timeout=1).json()) #this url to provide a predictable result
    except Exception as err:
        print("[ERROR] /js/status/bancho: ", err)
        return jsonify({
            "result" : 0
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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/actions/wipeap/<AccountID>")
def WipeAPRoute(AccountID: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 11):
        Account = GetUser(AccountID)
        WipeAutopilot(AccountID)
        RAPLog(session["AccountId"], f"has wiped the autopilot statistics for the account {Account['Username']} ({AccountID})")
        return redirect(f"/user/edit/{AccountID}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/actions/wiperx/<AccountID>")
def WipeRXRoute(AccountID: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 11):
        Account = GetUser(AccountID)
        WipeRelax(AccountID)
        RAPLog(session["AccountId"], f"has wiped the relax statistics for the account {Account['Username']} ({AccountID})")
        return redirect(f"/user/edit/{AccountID}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/actions/wipeva/<AccountID>")
def WipeVARoute(AccountID: int):
    """The wipe action."""
    if HasPrivilege(session["AccountId"], 11):
        Account = GetUser(AccountID)
        WipeVanilla(AccountID)
        RAPLog(session["AccountId"], f"has wiped the vanilla statistics for the account {Account['Username']} ({AccountID})")
        return redirect(f"/user/edit/{AccountID}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/actions/freeze/<id>")
def Freezee(id: int):
    if HasPrivilege(session["AccountId"], 6):
        Account = GetUser(id)
        FreezeHandler(id)
        RAPLog(session["AccountId"], f"has frozen the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)
@app.route("/actions/hwid/<id>")
def HWID(id: int):
    """Clear HWID matches."""
    if HasPrivilege(session["AccountId"], 6):
        Account = GetUser(id)
        ClearHWID(id)
        RAPLog(session["AccountId"], f"has cleared the HWID matches for the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)
@app.route("/actions/delete/<id>")
def DeleteAcc(id: int):
    """Account goes bye bye forever."""
    if HasPrivilege(session["AccountId"], 6):
        AccountToBeDeleted = GetUser(id)
        DeleteAccount(id)
        RAPLog(session["AccountId"], f"has deleted the account {AccountToBeDeleted['Username']} ({id})")
        return redirect("/users/1")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)
@app.route("/actions/kick/<id>")
def KickFromBancho(id: int):
    """Kick from bancho"""
    if HasPrivilege(session["AccountId"], 12):
        Account = GetUser(id)
        BanchoKick(id, "You have been kicked by an admin!")
        RAPLog(session["AccountId"], f"has kicked the account {Account['Username']} ({id})")
        return redirect(f"/user/edit/{id}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/actions/deletebadge/<id>")
def BadgeDeath(id:int):
    if HasPrivilege(session["AccountId"], 4):
        DeleteBadge(id)
        RAPLog(session["AccountId"], f"deleted the badge with the ID of {id}")
        return redirect(url_for("Badges"))
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/actions/createbadge")
def CreateBadgeAction():
    if HasPrivilege(session["AccountId"], 4):
        Badge = CreateBadge()
        RAPLog(session["AccountId"], f"Created a badge with the ID of {Badge}")
        return redirect(f"/badge/edit/{Badge}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/actions/createprivilege")
def CreatePrivilegeAction():
    if HasPrivilege(session["AccountId"], 13):
        PrivID = CreatePrivilege()
        RAPLog(session["AccountId"], f"Created a new privilege group with the ID of {PrivID}")
        return redirect(f"/privilege/edit/{PrivID}")
    redirect_url = request.url.replace("http", "https")
    return NoPerm(session, redirect_url)

@app.route("/actions/deletepriv/<PrivID>")
def PrivDeath(PrivID:int):
    if HasPrivilege(session["AccountId"], 13):
        PrivData = GetPriv(PrivID)
        DelPriv(PrivID)
        RAPLog(session["AccountId"], f"deleted the privilege {PrivData['Name']} ({PrivData['Id']})")
        return redirect(url_for("EditPrivileges"))
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)


#beatmaps.rankedby 변경함수
def beatmap_rankedby(text, bm):
    if text == "BeatmapID":
        mycursor.execute("UPDATE beatmaps SET rankedby = %s WHERE beatmap_id = %s", (session["AccountId"], bm))
        mydb.commit()
        log.info("비트맵 {} rankedby 변경".format(bm))
    elif text == "BeatmapSetID":
        mycursor.execute("UPDATE beatmaps SET rankedby = %s WHERE beatmapset_id = %s", (session["AccountId"], bm))
        mydb.commit()
        log.info("비트맵 셋 {} rankedby 변경".format(bm))

#바로 아래 코드 대비한 bsid to bid
def bsid_to_bid(bsid):
    mycursor.execute("SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = {}".format(bsid))
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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/action/loveset/<BeatmapSet>")
def LoveSet(BeatmapSet: int):
    if HasPrivilege(session["AccountId"], 3):
        SetBMAPSetStatus(BeatmapSet, 5, session)
        RAPLog(session["AccountId"], f"loved the beatmap set {BeatmapSet}")

        #rankedby 추가
        beatmap_rankedby("BeatmapSetID", BeatmapSet)

        return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

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
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/action/unrankset/<BeatmapSet>")
def UnrankSet(BeatmapSet: int):
    if HasPrivilege(session["AccountId"], 3):
        SetBMAPSetStatus(BeatmapSet, 0, session)
        RAPLog(session["AccountId"], f"unranked the beatmap set {BeatmapSet}")

        #rankedby 추가
        beatmap_rankedby("BeatmapSetID", BeatmapSet)

        return redirect(f"/rank/{bsid_to_bid(BeatmapSet)}")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/action/deleterankreq/<ReqID>")
def MarkRequestAsDone(ReqID):
    if HasPrivilege(session["AccountId"], 3):
        DeleteBmapReq(ReqID)
        return redirect("/rankreq/1")
    else:
        redirect_url = request.url.replace("http", "https")
        return NoPerm(session, redirect_url)

@app.route("/action/kickclan/<AccountID>")
def KickClanRoute(AccountID):
    if HasPrivilege(session["AccountId"], 15):
        KickFromClan(AccountID)
        return redirect("/clans/1")
    redirect_url = request.url.replace("http", "https")
    return NoPerm(session, redirect_url)

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
