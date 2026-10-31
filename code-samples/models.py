
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import time
from django.db.models.signals import post_save
from django.dispatch import receiver
from .services.scoring import ruleBase

# 1. User Model
class User(AbstractUser):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager', 'Manager'),
    )
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES , default='employee')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    
    def __str__(self):
        return f"{self.username} ({self.role})"

# 2. Attendance Model
class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now) # Automatically records today's date
    arrival_time = models.TimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"

# 3. Breach Model
class Breach(models.Model):
    LEVEL_CHOICES = (
        (1, 'High'),
        (2, 'Moderate'),
        (3, 'Low'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    level = models.IntegerField(choices=LEVEL_CHOICES)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - Breach Level: {self.level}"

# 4. Task Model
class Task(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    IMPORTANCE_CHOICES = (
        (1, "High"),
        (2, "Medium"),
        (3, "Low"),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)  
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    importance_degree = models.PositiveSmallIntegerField(choices=IMPORTANCE_CHOICES, default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    priority = models.CharField(max_length=20, default='medium')
    criteria = models.JSONField(default=dict, blank=True, null=True)
    def save(self, *args, **kwargs):
        if self.pk is not None:
            orig = Task.objects.get(pk=self.pk)
            # If the status changes to completed, record the completion time
            if orig.status != 'completed' and self.status == 'completed':
                self.completed_at = timezone.now()
            # If the manager reverts the completed status, clear the completion time
            elif orig.status == 'completed' and self.status != 'completed':
                self.completed_at = None
        else:
            if self.status == 'completed':
                self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

# 5. Evaluation Model
class Evaluation(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='evaluation')
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluations_given')
    
    objective_score = models.FloatField(null=True, blank=True, default=1.0) # Default task completion rate is 100%
    subjective_score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    final_score = models.FloatField(null=True, blank=True)

    def calculate_final_score(self,manual_attendance=None):
        task = self.task
        user = task.assigned_to
        today = timezone.now().date()

        # Fetch the latest breach in the same month (if any)
        breach = Breach.objects.filter(
            user=user,
            date__month=today.month,
            date__year=today.year
        ).order_by("-date").first()
        breach_level = breach.level if breach else None

        # Fetch today's attendance
        attendance = Attendance.objects.filter(user=user, date=today).first()
        arrival_time = attendance.arrival_time if attendance else None

        # Prepare data for the scoring engine (ruleBase)
        data = {
            "submissionTime": task.completed_at if task.completed_at else timezone.now(),
            "deadline": task.deadline,
            "taskNum": 1, # To be updated later if you need to fetch the total number of employee tasks
            "taskComplateAVR": self.objective_score or 1.0,
            "attendance_manual_score": manual_attendance,
            # Fixed working hours (can be moved to a Company Settings model later)
            "startWork": time(8, 0), 
            "endWork": time(16, 0),
            "arrivalTime": arrival_time,
            "startMeeting": time(10, 0),
            "endMeeting": time(11, 0),
            
            # Assume meeting attendance if the employee attended work 
            "arrivalMeeting": time(9, 55) if arrival_time else None,
            "breachLevel": breach_level,
            "importanceDegree": task.importance_degree,
        }

        rule = ruleBase(data)
        return rule.resultScore()

    def save(self, *args, **kwargs):
        manual_score = kwargs.pop('attendance_manual_score', None)
        
        # 🎯 Automation magic: 
        if self.task.completed_at:
            self.final_score = self.calculate_final_score(manual_attendance=manual_score)            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Evaluation for {self.task.title} - Score: {self.final_score}"

# 6. Signal for Automation
@receiver(post_save, sender=Task)
def create_evaluation_on_completion(sender, instance, created, **kwargs):
    # Once the task is submitted, the system automatically creates an evaluation for it
    if instance.status == 'completed' and instance.completed_at:
        Evaluation.objects.get_or_create(
            task=instance,
            defaults={'objective_score': 1.0} # Assume 100% completion until the manager updates it
        )