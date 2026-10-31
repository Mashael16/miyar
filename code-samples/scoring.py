from datetime import timedelta , time , datetime
import math

class ruleBase:

    def __init__(self,data):
        self.data = data
        self.submissionTime =data["submissionTime"]
        self.deadline = data["deadline"]
        self.taskNum = data.get("taskNum", 1)
        self.submissionScore = 0
        self.totalTaskScore = 0
        self.taskComplateAVR = data["taskComplateAVR"]
        self.ComplateScore = 0
        self.startWork = data["startWork"]
        self.endWork = data["endWork"]
        self.arrivalTime = data["arrivalTime"]
        self.startMeeting = data["startMeeting"]
        self.endMeeting = data["endMeeting"]
        self.arrivalMeeting = data["arrivalMeeting"]
        self.attendanceScore = 0
        self.dayNum = 0
        self.breachLevel = data.get("breachLevel")
        self.breachNum = 0
        self.totalBreachScore = 0
        self.importanceDegree = data["importanceDegree"]
        attendance_val = data.get("attendance_manual_score")
        self.attendance_manual_score = float(attendance_val) if attendance_val is not None else 100.0
   
    def submissionTimeRule(self):
        timeDifferent = self.submissionTime - self.deadline
        daysLate = math.ceil(timeDifferent.total_seconds() / (24*3600))

        if self.submissionTime <= self.deadline:
            return 100
        elif timeDifferent <= timedelta(hours=24):
            return 90 
        
        elif 2 <= daysLate <= 4:
            score = 90 - ((daysLate - 1) * 15)
            
            return max(0, score)
        else:
            return 0 
        

    def submissionAverage(self):
        if self.taskNum == 1:
            self.submissionScore = 0
        self.submissionScore += self.submissionTimeRule()
        return self.submissionScore / self.taskNum


    def taskComplate(self):


        score = self.taskComplateAVR * 100
        return max(0, min(100, score))
    
    def taskComplateScore(self):
        if self.taskNum == 1:
            self.ComplateScore = 0
        self.ComplateScore += self.taskComplate()
        return self.ComplateScore / self.taskNum



    def importance(self):
        submissionDeduction = 100 - self.submissionTimeRule()
        taskComplateDeduction = 100 - self.taskComplate()
        
        totalDeduction = submissionDeduction + taskComplateDeduction
        

        if self.importanceDegree == 1: 
            taskImportanceDeduction = totalDeduction * 1.5
        elif self.importanceDegree == 2:
            taskImportanceDeduction = totalDeduction * 1.0
        else:
            taskImportanceDeduction = totalDeduction * 0.5 
        
            
        importanceScore = 100 - taskImportanceDeduction
        return max(0, importanceScore)


    def workTime(self):
        today = datetime.today().date()
        start_datetime = datetime.combine(today, self.startWork)
        start_meetingtime = datetime.combine(today, self.startMeeting)
        
        manual_score = self.data.get("attendance_manual_score")
        
        if manual_score is not None:
            return float(manual_score)
        
        if self.arrivalTime is None:
            return 50 
        final_score = 100
        arrival_datetime = datetime.combine(today, self.arrivalTime)
        workDelay = arrival_datetime - start_datetime

        if workDelay >= timedelta(minutes=15):
            delayMinutes = workDelay.total_seconds() / 60
            timeDelay = math.ceil(delayMinutes / 15)
            final_score -= (timeDelay * 5) 
            

        if self.arrivalMeeting is None:
            final_score -= 20
        else:
            arrival_meetingtime = datetime.combine(today, self.arrivalMeeting)
            meetingDelay = arrival_meetingtime - start_meetingtime
            if timedelta(minutes=5) <= meetingDelay <= timedelta(minutes=10):
                final_score -= 10
            elif meetingDelay > timedelta(minutes=10):
                final_score -= 15

        return max(0, final_score)

    def workTimeAverage(self):
        if datetime.now().day == 1:
            self.attendanceScore = 0
            self.dayNum = 0
        self.attendanceScore += self.workTime()
        self.dayNum += 1
        return self.attendanceScore / self.dayNum


    def Breaches(self):
        if self.breachLevel is None or self.breachLevel == 'none':
            breachScore = 100
        elif self.breachLevel == 1: # High Breach
            breachScore = 0  
            
        elif self.breachLevel == 2: # Moderate
            breachScore = 50
        elif self.breachLevel == 3: # Low
            breachScore = 80
        else:
            breachScore = 100
            
        if datetime.now().day == 1:
            self.totalBreachScore = 0
            self.breachNum = 0

        self.totalBreachScore += breachScore
        self.breachNum += 1
        return self.totalBreachScore / self.breachNum


    def resultScore(self):
        # الأوزان الجديدة:
        # 40% جودة المهمة (أهم شيء)
        # 20% وقت التسليم
        # 20% المخالفات والسلوك
        # 10% الحضور
        # 10% عامل الأهمية
        
        score_100 = (self.taskComplateScore() * 0.40) + \
                    (self.submissionAverage() * 0.20) + \
                    (self.Breaches() * 0.20) + \
                    (self.attendance_manual_score * 0.10) + \
                    (self.importance() * 0.10)
                    
        score_5 = score_100 / 20
        return round(score_5, 1) 
    