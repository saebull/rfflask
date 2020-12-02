import pandas as pd
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from flask import Flask, render_template, redirect, request, url_for
import requests
from bs4 import BeautifulSoup
import re
import heapq

cred = credentials.Certificate('ongkey.json')
defaul_app = firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://ie-project-292614.firebaseio.com/'
})

keyname = db.reference('/p1lat').get().keys()
p1lat = db.reference('/p1lat').get().values()
p1lng = db.reference('/p1lng').get().values()
p2lat = db.reference('/p2lat').get().values()
p2lng = db.reference('/p2lng').get().values()
lat = db.reference('/lat').get().keys()
lng = db.reference('/lng').get().keys()
df = pd.DataFrame({'p1위도':list(p1lat),'p1경도':list(p1lng),
                       'p2위도':list(p2lat),'p2경도':list(p2lng)})
df2 = pd.DataFrame({'도로명':list(keyname)})
df3 = pd.DataFrame({'도로명':list(keyname),'위도':list(lat),'경도':list(lng)})
ref = db.reference('/road')
lst = ref.get()

score = db.reference('/score')
sc = score.get()
key = sc.keys()
value = sc.values()
keylst=[]
for r_n in key:
    keylst.append(r_n)
sc_lst = []
for i in value:
    sc_lst.append(i['score'])
data = pd.DataFrame({'도로명':keylst,'합계':sc_lst})

def getlatlng(address):
    base_url = "https://maps.googleapis.com/maps/api/geocode/xml?address="
    url = base_url + address + "CA&key=AIzaSyBHLxYz1nqgbaj-SIxnBXtvWiLiXAr1LNQ"
    res = requests.get(url)
    html = BeautifulSoup(res.text,'html.parser')
    lat = re.sub('<[^>]*>', '',str(html.select("location > lat")) ,0)##위도
    lng = re.sub('<.+?>', '',str(html.select("location > lng")) ,0) ##경도
    lat = float(lat.replace('[', '').replace(']', ''))
    lng = float(lng.replace('[', '').replace(']', ''))
    return lat,lng

def getPos(x, y):
    x = float(x)
    y = float(y)
    position1=[]
    position2 =[]
    for i in range(len(df)):
        if abs(x - df.loc[i,'p1위도']) + abs(y - df.loc[i,'p1경도']) > abs(x - df.loc[i,'p2위도']) + abs(y - df.loc[i,'p2경도']):
            position1.append([i,abs(x - df.loc[i,'p1위도']) + abs(y - df.loc[i,'p1경도'])])
        else:
            position2.append([i,abs(x - df.loc[i,'p2위도']) + abs(y - df.loc[i,'p2경도'])])
    minn = 1000
    result1 =0
    result2 = 0
    if min(position1[1]) > min(position2[1]):
        for j in position1 :
            if minn > j[1]:
                minn = j[1]
                result1 = j[0]
    else:
        for j in position2 :
            if minn > j[1]:
                minn = j[0]
                result2 = j[0]

    if result1 >0:
        road =df2.loc[result1,'도로명']
        return road
    else :
        road =df2.loc[result2,'도로명']
        return road

def dijkstra(graph, start, end):
    visited = {start: 0}
    h = [(0, start)]
    path = {}
    lst=[]
    distances = {vertex: float('inf') for vertex in graph} # 시작점과 모든 정점과의 사리의 거리를 무한으로 지정
    #istances[start] = [0, start] # 시작점과 시작점 사이의 거리 0
    #queue = [] # [[거리,정점]]
    #print(distances[start][0])
    #heapq.heappush(queue, [distances[start][0], start])
    while distances:
        current_distance, current_vertex = heapq.heappop(h)
        try:
            while current_vertex not in distances:
                current_distance, current_vertex = heapq.heappop(h)
        except IndexError:
             break
        #if distances[current_vertex][0] < current_distance:
            #continue

        if current_vertex == end:
            way = end
            lst.append(way)
            path_output = end + '->'
            while path[way] != start:
                path_output += path[way] + '->'
                way = path[way]
                lst.append(way)
            lst.append(start)
            path_output += start
            print(path_output)

            return visited[end], path, lst

        del distances[current_vertex]

        for v, weihgt in graph[current_vertex].items():
            weihgt = current_distance + weihgt
            #if weihgt < distances[adjacent][0]: # 현재까지 시작정점과 현재정점사이의 거리보다 짧다면
                #distances[adjacent] = [dis, current_vertex] # 현재정점과 시작정점 사이의 거리 업데이트
                #heapq.heappush(queue, [dis, adjacent])

            if v not in visited or weihgt < visited[v] :
                visited[v] = weihgt
                heapq.heappush(h,(weihgt,v))
                path[v] = current_vertex


    return visited,path,lst

def findlatlng(name):
    lat = df3[df3['도로명']==name].loc[:,'위도'].values
    lng = df3[df3['도로명']==name].loc[:,'경도'].values
    return lat,lng

total = []
def dfs_paths(graph, start, end, visited=[],weight = [0]):
    visited = visited + [start]

    if len(visited) > 1 :
        a = lst[visited[-2]][start]
        weight = weight + [a]
    # 도착할 경우, paths에 경로를 기록한다.
    if start == end:
        total.append([visited,sum(weight)])
        #paths.append(visited)
        #totalweight.append(sum(weight))

    # 현재 노드의 자손 노드들 중, 방문하지 않은 노드들에 대해 재귀 호출
    for node, k in graph[start].items():
        if node not in visited:
            if len(visited) >= 10:
                continue
            dfs_paths(graph, node, end, visited, weight)
    total.sort(key=lambda x: x[1])

    return total
def calscore(lst):
    temp = []
    for i, j in lst[0:3]:
        score = 0
        for h in i:
            for index,k in enumerate(data['도로명']):
                if h == k:
                    score += data.loc[index,'합계']
        temp.append([i,score,j])
    temp.sort(key=lambda x: x[1])
    return temp[0][0], temp[0][2]

app = Flask(__name__)

@app.route('/')
def inputTest():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    if request.method == 'POST':
       dep = request.form['departure']
       des = request.form['destination']
       dep_lat, dep_lng = getlatlng(dep)
       des_lat, des_lng = getlatlng(des)
       s = getPos(dep_lat, dep_lng)
       e = getPos(des_lat, des_lng)
       dfs = dfs_paths(lst,s,e)
       temp = []
       b,c = calscore(dfs)
       for i in b:
           ss,ee = findlatlng(i)
           temp.append((ss[0],ee[0]))


       return render_template("generic.html", dep=dep, des=des, dep_lat=dep_lat, dep_lng=dep_lng, des_lat=des_lat, des_lng=des_lng, temp=temp)

@app.route('/result2', methods=['POST'])
def result2():
    if request.method == 'POST':
       dep = request.form['departure']
       des = request.form['destination']
       dep_lat, dep_lng = getlatlng(dep)
       des_lat, des_lng = getlatlng(des)
       s = getPos(dep_lat, dep_lng)
       e = getPos(des_lat, des_lng)
       (a, b, c) = dijkstra(lst, s, e)
       temp = []
       for i in c:
           ss,ee = findlatlng(i)
           temp.append((ss[0],ee[0]))
       temp.reverse()
       return render_template("elements.html", dep_lat=dep_lat, dep_lng=dep_lng, des_lat=des_lat, des_lng=des_lng, temp=temp)

@app.route('/elements')
def elements():
       return render_template('elements.html')

@app.route('/index')
def index():
       return render_template('index.html')

@app.route('/generic')
def generic():
       return render_template('generic.html')


if __name__ == '__main__':
    app.run()
