import json
from datetime import datetime
import time
import re
import requests
from bs4 import BeautifulSoup
from prettytable import PrettyTable

urls = {
    "LongView Apartments" : "https://www.equityapartments.com/greater-boston/waltham/longview-place-apartments#/unit-availability-tile",
    "Avalon Sagus" : "https://www.avaloncommunities.com/massachusetts/saugus-apartments/avalon-saugus/apartments?bedroom=2BD",
    "Currents on Charles" : "https://www.udr.com/boston-apartments/waltham/currents-on-the-charles/apartments-pricing/?beds=2" 
}

def current_time_millis():
    return round(time.time() * 1000)

# link for extract html data 
def getdata(url): 
    r = requests.get(url) 
    return r.text 

def getLastExecutionRunTimeMillis():
     with open('out/runStats.txt', 'r') as f:
        lastLine = f.readlines()[-1]
        return lastLine

def getLastRunTime():
    lastRunDateTime = datetime.fromtimestamp(float(getLastExecutionRunTimeMillis())/1000)
    return (lastRunDateTime)

def getNextRefresh():
    hours = 10
    totalSecs = 10 * 3600
    nextRunDateTime = datetime.fromtimestamp(float(getLastExecutionRunTimeMillis())/1000 + totalSecs)
    return nextRunDateTime

def saveCurrentExecutionTimeStamp():
    # Save run timestamps
    runStatsFile = open("out/runStats.txt", "a+")
    runStatsFile.write(str(current_time_millis()) + "\n")
    runStatsFile.close()
    print("[INFO] Saved execution timestamp")   
  
def getAvailableApartments(url, sortBy):
    avalonData = getdata(url)
    avalonSoup = BeautifulSoup(avalonData, "html.parser")
    # #  parsing static avalon sagus page saved in folder
    # with open("test/sagus.html") as sagusStaticHtmlFile:
    #     avalonSoup = BeautifulSoup(sagusStaticHtmlFile, "html.parser")
    
    availableApartments = avalonSoup.find("ul", class_="apartment-cards available")
    allCards = availableApartments.findChildren("a", recursive=True)

    # Specify the Column Names while initializing the Table 
    myTable = PrettyTable(["Apartment Number", "  Availability  ", "      Price      ", "   Size   ", "   Lease Length   ", "        Type        ", "      Status      "]) 

    for card in allCards:
        content = card.find("div", class_="content")
        apartmentNumber = content.find("div", class_="title brand-main-text-color").get_text().replace("Apartment", "")
        details = content.find("div", class_="details").get_text()
        size = details[len(details)-10:]
        description = details[:len(details)-12]
        priceDiv = content.find("div", class_="price").get_text()
        leaseDuration = priceDiv[len(priceDiv)-12:len(priceDiv)-6].replace("mo", "months")
        price = priceDiv[:len(priceDiv)-16].replace(" ", " or ")
        availability = content.find("div", class_="availability").get_text().replace("Available ", "")
        status = ""
        if "apr" in availability.lower() or "may" in availability.lower() :
            status = " >>> Follow up"
        if "$3" in price :
            status = " expensive " + status 
        if "10" in size[0:3] :
            status = "small space " + status        
        # Add row
        myTable.add_row([apartmentNumber, availability, price, size, leaseDuration, description, status])
    
    # sort results
    myTable.sortby = sortBy
    myTable.reversesort = True
    return(myTable)

def getAvailableApartmentsFromLongview():
    data = getdata(urls.get("LongView Apartments"))
    soup = BeautifulSoup(data, "html.parser")

    # Specify the Column Names while initializing the Table 
    myTable = PrettyTable(["Apartment Number", "  Availability  ", "      Price      ", "   Size   ", "   Lease Length   ", "        Type        ", "      Status      ", "Features"]) 

    # with open("test/longview.html") as tempHtmlFile:
    #     soup = BeautifulSoup(tempHtmlFile, "html.parser")

    data = soup.find("div", class_="data-view")
    twoBedUnits = data.find_all("div", class_="units")[1]     
    units = twoBedUnits.findChildren("div", recursive=False)
    for unit in units :
        aptNumber = str(unit)[27:57].strip().replace('buildingId: ', 'B-').replace(', unitId: ', ', Apt-')
        unitData = re.sub('\s+',' ',unit.get_text().replace("\n", ' ').strip())
        price = unitData[:6]
        availability = unitData[60:69].split('/',2)
        availabilityMonth = availability[0]
        availabilityDate = availability[1]
        if availabilityMonth == '2' :
            availabilityMonth = 'Feb'
        elif availabilityMonth == '3' :
            availabilityMonth = 'Mar'
        elif availabilityMonth == '4' :
            availabilityMonth = 'Apr'
        elif availabilityMonth == '5' :
            availabilityMonth = 'May' 

        size = unitData[27:38].strip().replace('.','')
        type = "2B-2B | " + unitData[42:50].strip()
        features = unitData[unitData.find('Now')+4:]
        leaseLength = unitData[7:12]
        status = ''
        if availabilityMonth == 'Apr' or availabilityMonth == 'May' :
            status = " >>> Follow up"
        if "$3" in price :
            status = " expensive " + status 
        if "10" in size[0:3] :
            status = "small space " + status        
        # Add row
        myTable.add_row([aptNumber, availabilityMonth + ' ' + availabilityDate, price, size, leaseLength, type, status, features])
    myTable.sortby = "  Availability  "
    myTable.reversesort = True
    return(myTable)
    
def getAvailableApartmentsCurrentOnCharles():
    units = [] 
    data = getdata(urls.get("Currents on Charles"))
    soup = BeautifulSoup(data, "html.parser")
    # #  parsing static avalon sagus page saved in folder
    # with open("test/currents.html") as tempHtmlFile:
    #     soup = BeautifulSoup(tempHtmlFile, "html.parser")

    scripts = soup.find_all("script")
    # Specify the Column Names while initializing the Table 
    myTable = PrettyTable(["Apartment Number", "  Availability  ", "      Price      ", "   Size   ", "   Lease Length   ", "        Type        ", "      Status      "]) 

    for script in scripts:
        if "window.udr.jsonObjPropertyViewModel" in script.get_text():
            scriptText = script.get_text().replace("window.udr.jsonObjPropertyViewModel = ", "").replace("window.udr.jsonObjPropertyViewModel.allSpecials = [];", "").strip()
            scriptJson = json.loads(scriptText[0: len(scriptText)-1])
            units = scriptJson["floorPlans"][0]["units"]
            break

    for unit in units :
        # Add row
        dateMillis = unit['availableDate'].replace('/Date(','').replace(')/','').strip()
        status = ''
        dateAvailable = datetime.fromtimestamp(float(dateMillis)/1000).strftime("%b %d")
        if "apr" in dateAvailable.lower() or "may" in dateAvailable.lower() :
            status = " >>> Follow up"
        size =  str(unit['sqFt'])+ " sqft"
        price = str(unit["rentMax"])[:4] 
        price = '$' + price[:1] + ',' + price[1:]
        myTable.add_row([unit["unitName"], dateAvailable, price, size , 'N/A', unit["floorPlanName"], status])  
    myTable.sortby = "  Availability  "
    myTable.reversesort = True
    return(myTable)

#save results to a file
def writeResults():
    avalonResults = getAvailableApartments(urls.get("Avalon Sagus"), "  Availability  ")
    longviewResults = getAvailableApartmentsFromLongview()
    currentsResults = getAvailableApartmentsCurrentOnCharles()

    with open('out/results.txt', 'w') as w:
        w.write("\nCreated at : " +  datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")+"\n")
        w.write('\n-------------\n AVALON SAGUS\n-------------\n')
        w.write(str(avalonResults))
        w.write('\n-------------------\n LONGVIEW APARTMENTS \n-------------------\n')
        w.write(str(longviewResults))
        w.write('\n--------------------\n CURRENTS AT CHARLES \n--------------------\n')
        w.write(str(currentsResults))
    print("[INFO] Updated results.txt")    

def printResultsFile():
    with open('out/results.txt') as f:
        contents = f.read()
    print(contents)


def main():
    # write to file updated values if now > next refresh
    if time.time() > getNextRefresh().timestamp() :
        print("\n[INFO] Refreshing results now . . . ")
        writeResults()
        saveCurrentExecutionTimeStamp()
        printResultsFile()
        print("\n[INFO] End\n")
    else :
        print('Last Updated at : ' + getLastRunTime().strftime("%m/%d/%Y, %I:%M:%S %p"))
        print('Next Refresh at : ' + getNextRefresh().strftime("%m/%d/%Y, %I:%M:%S %p") +' (every 10 hours))')
        printResultsFile()

# for enabling python script execution using Command Line
if __name__ == "__main__":
    main()
    