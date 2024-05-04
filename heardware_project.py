import micropython
import time
from filefifo import Filefifo
from fifo import Fifo
from machine import ADC, Pin, I2C
from ssd1306 import SSD1306_I2C
import network
import urequests as requests 
import ujson
from time import sleep
from umqtt.simple import MQTTClient


file_path = "ownData.txt"

interval_between_data_points = 50
sample_count_between_30_seconds = 30000 / interval_between_data_points

WIFI_NAME="KMD652_Group_11"
WIFI_PASS="Group_11_FSM"

#MQTT_BROKER = "mqtt-dashboard.com"
#MQTT_TOPIC = "HRV_DATA"
#MQTT_CLIENT_ID = "RPI_PICO_GROUP_11"
MQTT_BROKER = "192.168.11.253"
MQTT_TOPIC = "Group_11_FSM"
MQTT_CLIENT_ID = "KMD652_Group_11"

################# OLED INIT #######################

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)
oled.fill(0)

###################################################


################## Global State Variables #######################
current_time = 0
current_time_plot = 0
calibrated_interval = 0
calculation_frame = []
calculation_frame_max = None
calculation_frame_min = None

history_array = []


#################################################################


# This class stores HRV Data

class HRVData:
    def __init__(self, calculation_type="local", mean_hr=0, mean_ppi=0, rmssd=0, sdnn=0, sns=0.0, pns=0.0):
        self._mean_hr = mean_hr
        self._mean_ppi = mean_ppi
        self._rmssd = rmssd
        self._sdnn = sdnn
        self._sns = sns
        self._pns = pns
        self._calculation_type = calculation_type
        
    def get_calculation_type(self):
        return self._calculation_type

    def set_calculation_type(self, value):
        self._calculation_type = value

    def get_mean_hr(self):
        return self._mean_hr

    def set_mean_hr(self, value):
        self._mean_hr = value

    def get_mean_ppi(self):
        return self._mean_ppi

    def set_mean_ppi(self, value):
        self._mean_ppi = value

    def get_rmssd(self):
        return self._rmssd

    def set_rmssd(self, value):
        self._rmssd = value

    def get_sdnn(self):
        return self._sdnn

    def set_sdnn(self, value):
        self._sdnn = value

    def get_sns(self):
        return self._sns

    def set_sns(self, value):
        self._sns = value

    def get_pns(self):
        return self._pns

    def set_pns(self, value):
        self._pns = value

    def to_json(self):
        return {
            "calculation_type": self._calculation_type,
            "mean_hr": self._mean_hr,
            "mean_ppi": self._mean_ppi,
            "rmssd": self._rmssd,
            "sdnn": self._sdnn,
            "sns": self._sns,
            "pns": self._pns
        }



def push_to_history(hrv_data):
    if len(history_array)<6:
        history_array.append(hrv_data)
    else:
        for i in range(len(history_array)-1):
            history_array[i] = history_array[i+1]
        history_array[5] = hrv_data
    

def print_hrv(hrv_data):
    oled.fill(0)
    
    display_text(f"MEAN HR: {hrv_data.get_mean_hr()}",1)
    display_text(f"MEAN PPI: {hrv_data.get_mean_ppi()}",2)
    display_text(f"RMSSD: {hrv_data.get_rmssd()}",3)
    display_text(f"SDNN: {hrv_data.get_sdnn()}",4)
    display_text(f"SNS: {hrv_data.get_sns()}",5)
    display_text(f"PNS: {hrv_data.get_pns()}",6)

    oled.show()
    
# This class is made to get the data from different sources by changing the class constructor.
# Without and parameter the adapter will try to get data from ADC Pin 26. These behavior can be
# modified based on constructor parameter.
class DataAdapter:
    file_path = None;
    pin = 26;
    mode = 0
    hr_sensor = None
    file_data_fifo = None;

    def __init__(self, file_path=None, pin=None):
        if file_path != None:
            self.file_path = file_path
            self.mode = 1
            self.file_data_fifo = Filefifo(10, name=self.file_path)
        else:
            self.mode = 0
            if pin != None:
                self.pin = pin
            self.hr_sensor = ADC(Pin(self.pin, Pin.IN))

    def get(self):
        if self.mode == 0:
            time.sleep(.05)
            return self.hr_sensor.read_u16()
        
        else:
            return self.file_data_fifo.get()


def calculate_min_max(sample, calculation_frame_max, calculation_frame_min):
    max = calculation_frame_max
    min = calculation_frame_min
    if calculation_frame_max == None:
        max = sample
    else:
        if calculation_frame_max < sample:
            max = sample

    if calculation_frame_min == None:
        min = sample
    else:
        if calculation_frame_min > sample:
            min = sample
    return max, min


prepare_counter = 1


def store_processed_information(bpm, ppi):
    global PPI_ARRAY
    global BPM_ARRAY
    global prepare_counter
    global MEAN_BPM
    global MEAN_PPI

    bpm_sum = 0
    ppi_sum = 0

    if len(PPI_ARRAY) == 120:
        for i in range(119):
            PPI_ARRAY[i] = PPI_ARRAY[i + 1]
            BPM_ARRAY[i] = BPM_ARRAY[i + 1]
            ppi_sum += PPI_ARRAY[i]
            bpm_sum += BPM_ARRAY[i]
        PPI_ARRAY[119] = ppi
        BPM_ARRAY[119] = bpm
        ppi_sum += ppi
        bpm_sum += bpm
        if prepare_counter < 120:
            prepare_counter += 1
    else:
        PPI_ARRAY.append(ppi)
        BPM_ARRAY.append(bpm)

    MEAN_BPM = int(bpm_sum / 120)
    MEAN_PPI = int(ppi_sum / 120)
    #print(MEAN_BPM,MEAN_PPI)



def calculate_hrv(PPI_ARRAY,BPM_ARRAY):
    RMSSD = 0
    SDNN = 0
 
    MEAN_PPI = 0
    MEAN_BPM = 0
    
    ppi_sum = 0
    bpm_sum = 0
    
    for i in range(len(PPI_ARRAY)):
        ppi_sum += PPI_ARRAY[i]
        bpm_sum += BPM_ARRAY[i]
 
    
    MEAN_PPI = ppi_sum//len(PPI_ARRAY)
    MEAN_BPM = bpm_sum//len(PPI_ARRAY)

    sqr_sum_RMSSD = 0
    sqr_sum_SDNN = 0

    i = 0
    while i < len(PPI_ARRAY):
        if i < len(PPI_ARRAY) - 1:
            sqr_sum_RMSSD += (PPI_ARRAY[i + 1] - PPI_ARRAY[i]) ** 2

        sqr_sum_SDNN += (PPI_ARRAY[i] - MEAN_PPI) ** 2
        i += 1

    RMSSD = round((sqr_sum_RMSSD / (len(PPI_ARRAY) - 1)) ** (1 / 2), 0)
    SDNN = round((sqr_sum_SDNN / (len(PPI_ARRAY) - 1)) ** (1 / 2), 0)
    
    return HRVData ("P",MEAN_BPM,MEAN_PPI,RMSSD,SDNN)


def calculate_threshold(data_20, sample):
    sum_data = 0
    max = sample
    min = sample
    threshold = 0
    
    if len(data_20) >= 20:
        for i in range (len(data_20)-1):
            data_20[i] = data_20[i+1]
            if max > data_20[i] :
                max = data_20[i]
            if min < data_20[i] :
               min = data_20[i]
               
        data_20[19] = sample
        threshold = (max + min )*.50
    else:
        data_20.append(sample)
        
    return threshold

def process_data_for_latest_30_second(is_kubios):
    global calculation_frame
    previous_peak_time = 0

    global HRV_calculated

    frame_peaks = []
    PPI_ARRAY = []
    BPM_ARRAY = []
    data_20 = []

    frame_peak_count = 0
    previous_slop_sign = 0
    slope = 0
    threshold=0
    
    previous_datapoint = None
    
    for frame_sample in calculation_frame:
        value = frame_sample[1]
    
        frame_time = frame_sample[0]
        threshold = calculate_threshold(data_20,value)
        
        if threshold ==0:
            continue
        
        if value > threshold:
            if previous_datapoint != None:
                slope = (value - previous_datapoint)

                if previous_slop_sign >= 0 and slope < 0:
                    ppi = frame_time - previous_peak_time
                    if previous_peak_time == 0 or ppi >= 250 and ppi <= 2000:
                        frame_peak_count = frame_peak_count + 1
                        frame_peaks.append((frame_time, value))
                        if previous_peak_time != 0:
                            bpm = int(60000 / ((ppi)))
                            if (bpm > 30):
                                PPI_ARRAY.append(ppi)
                                BPM_ARRAY.append(bpm)

                        previous_peak_time = frame_time

            previous_datapoint = value
            previous_slop_sign = slope
 
            
    if not is_kubios:
        hrv_data = calculate_hrv(PPI_ARRAY,BPM_ARRAY)
        push_to_history(hrv_data)
        
        if connect_to_internet():
            send_to_mqtt(hrv_data)
        
        print_hrv(hrv_data)
        HRV_calculated = True
    else:
        sending_data_to_kubios(PPI_ARRAY)
    


max_with_time = None
min_with_time = None

x1 = 0
y1 = 0
x2 = 0
y2 = 0

val1 = -1;
val2 = -1;

previous_rel_sample = 0
previous_rel_ms = 0
previous_rel_peak_time = 0
plot_HR = 0
plot_PPI = 1
peak_calculated = False
 
def plotData(sample):
    global val1
    global val2
    global val3
    global x1
    global y1
    global x2
    global y2
    global max_with_time
    global min_with_time
    global calibrated_interval
    global plot_HR
    global current_time_plot
    global previous_rel_sample
    global previous_rel_peak_time
    global plot_PPI, peak_calculated
      
    rel_threshold = 12
    
    moving_avg_sample = sample
    
    if max_with_time == None:
        min_with_time = (moving_avg_sample, current_time_plot)
        max_with_time = (moving_avg_sample, current_time_plot)
    
    if sample > max_with_time[0] or current_time_plot - max_with_time[1] > calibrated_interval*150:   # 504 to discard the very old max
        max_with_time = (moving_avg_sample, current_time_plot)
        
    if sample < min_with_time[0] or current_time_plot - min_with_time[1] > calibrated_interval*150:
        min_with_time = (moving_avg_sample, current_time_plot)
    
    
    rel_max = max_with_time[0] - min_with_time[0]
    
    rel_sample = moving_avg_sample - min_with_time[0]
    
    if rel_max==0:
        rel_max = 1
    
    x2 += 2
    if x2> 128:
       x2 = 0
    y2 = 64-(30*rel_sample//rel_max + 5)
    
    
    val3 = 50*rel_sample//rel_max +5
    if   val1 !=1:
        val3 = (val1 + val3) //3
        
   
    if val3>rel_threshold and previous_rel_sample>val3 and peak_calculated == False:
        plot_PPI_temp = current_time_plot-previous_rel_peak_time
        if plot_PPI_temp>0 :
            plot_HR_temp = int(60*1000/(plot_PPI_temp))
            
            if plot_HR_temp>=30 and plot_HR_temp<=240:
                plot_HR = plot_HR_temp
                plot_PPI = plot_PPI_temp

            
        previous_rel_peak_time = current_time_plot
        peak_calculated = True

    if  previous_rel_sample<val3:
       peak_calculated = False


    oled.fill_rect(x1, 0, 4, oled_height, 0)

    oled.fill_rect(0, 0, oled_width, 10, 0)
    
    if plot_HR == 0:
        oled.text(f"Calibrating ...", 0, 0)
    else:
        oled.text(f"HR: {plot_HR}, {plot_PPI}ms", 0, 0)
    
    if(x2>x1) :
        oled.line(x1, y1, x2, y2, 4)

    x1 = x2
    y1 = y2
    
    oled.show()
    val1 = val3
    previous_rel_sample = val3
    current_time_plot = current_time_plot + calibrated_interval


x =0
calibrated = False


class Encoder:
    def __init__(self, rot_a, rot_b):
        self.a = Pin(rot_a, mode = Pin.IN, pull = Pin.PULL_UP)
        self.b = Pin(rot_b, mode = Pin.IN, pull = Pin.PULL_UP)
        self.fifo = Fifo(30, typecode = 'i')
        self.a.irq(handler = self.handler, trigger = Pin.IRQ_RISING, hard = True)
    def handler(self, pin):
        if self.b():
            self.fifo.put(-1)
        else:
            self.fifo.put(1)


def operation_1_HR():
    global calibrated
    global current_time
    global calibrated_interval
    if HR_measure_started == False:
        oled.fill(0)
        display_centered_text("",1)
        display_centered_text("START",2)
        display_centered_text("MEASUREMENT",3)
        display_centered_text("BY PRESSING",4)
        display_centered_text("THE BUTTON",5)
        oled.show()
        calibrated = False
        current_time = 0
    else:
        current_milliseconds = time.time_ns()
        sample = data.get()
        plotData(sample)
        current_milliseconds2 = time.time_ns()
     
        if calibrated == False:
           calibrated = True
           calibrated_interval = (current_milliseconds2 - current_milliseconds) // 1000000


HRV_calculated = False
def operation_2_3_HRV(is_kubios):
    global current_time        
 
    if HRV_calculated:
        return
    sample = data.get()

    remaining = 0
    
    frame_length = len(calculation_frame)
    if len(calculation_frame) == sample_count_between_30_seconds:
        oled.fill(0)
        display_centered_text("",1)
        display_centered_text("",2)
        display_centered_text("",3)
        display_centered_text("Analyzing ...",4)
        oled.show()
        process_data_for_latest_30_second(is_kubios)
    else:
        remaining = (30000-frame_length*interval_between_data_points)
        if remaining%1000 ==0:
            oled.fill(0)
            display_centered_text("",1)
            display_centered_text("",2)
            display_centered_text("Collecting ...",3)
            display_centered_text(str(remaining//1000),4)
            oled.show()
            
    calculation_frame.append((current_time, sample))

    # Update Data
    current_time = current_time + interval_between_data_points
    
    
def send_to_mqtt(hrv_data):
    
    message = ujson.dumps(hrv_data.to_json())

    try:
        oled.fill(0)

        display_centered_text("",1)
        display_centered_text("",2)
        display_centered_text("Sending data",3)
        display_centered_text("to Mqtt",4)

        oled.show()

         # Create MQTT client instance
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)

        # Connect to MQTT broker
        mqtt_client.connect()

        # Publish message
        mqtt_client.publish(MQTT_TOPIC, message)

        # Disconnect from MQTT broker
        mqtt_client.disconnect()
        time.sleep(1)

    except Exception as e:
        oled.fill(0)

        display_centered_text("",1)
        display_centered_text("Failed to",2)
        display_centered_text("Send data",3)
        display_centered_text("to Mqtt!",4)

        oled.show()
        
        time.sleep(2)
        

def connect_to_internet():
    global  WIFI_NAME, WIFI_PASS
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_NAME, WIFI_PASS)

    retry_count = 18
    while not wlan.isconnected() and retry_count>0:
        oled.fill(0)
        display_centered_text("",1)
        display_centered_text("",2)
        display_centered_text("Checking WiFi",3)
        if retry_count%3 ==0:
            display_centered_text(".",4)
        if retry_count%3 ==2:
            display_centered_text("..",4)
        if retry_count%3 ==1:
            display_centered_text("...",4)
        oled.show()
        time.sleep(.5)
        retry_count -= 1
    
    if not wlan.isconnected() :
        oled.fill(0)
        display_centered_text("",1)
        display_centered_text("Unable to",2)
        display_centered_text("Connect to",3)
        display_centered_text("the Internet",4)
        oled.show()
        
    return wlan.isconnected()

def sending_data_to_kubios(data):
    global calculation_frame, HRV_calculated
    
    if not connect_to_internet() :  
        HRV_calculated = True
    else:
        APIKEY = "pbZRUi49X48I56oL1Lq8y8NDjq6rPfzX3AQeNo3a" 
        CLIENT_ID = "3pjgjdmamlj759te85icf0lucv" 
        CLIENT_SECRET = "111fqsli1eo7mejcrlffbklvftcnfl4keoadrdv1o45vt9pndlef" 
        TOKEN_URL = "https://kubioscloud.auth.eu-west-1.amazoncognito.com/oauth2/token" 

        response = requests.post( 
            url = TOKEN_URL, data = 'grant_type=client_credentials&client_id={}'.format(CLIENT_ID), 
            headers = {'Content-Type':'application/x-www-form-urlencoded'}, auth = (CLIENT_ID, CLIENT_SECRET)) 
        response = response.json()  
        access_token = response["access_token"]  

        data_set = {
            "type": "RRI",
            "data": data,
            "analysis": {
            "type": "readiness"}
            }

        response = requests.post( url = "https://analysis.kubioscloud.com/v2/analytics/analyze", 
            headers = { "Authorization": "Bearer {}".format(access_token), 
             "X-Api-Key": APIKEY }, 
            json = data_set)  
        response = response.json() 
        
        hrv_data = HRVData ("K",int(response['analysis']['mean_hr_bpm']),
                            int(response['analysis']['mean_rr_ms']),
                            int(response['analysis']['rmssd_ms']),
                            int(response['analysis']['sdnn_ms']),
                            float(response['analysis']['sns_index']),
                            float(response['analysis']['pns_index']))
        
        push_to_history(hrv_data)
        send_to_mqtt(hrv_data)
        print_hrv(hrv_data)

        HRV_calculated = True
        
      

def operation_3_History(pointer):
    global history_showed
    
    if len(history_array) == 0:
        oled.fill(0)
        display_centered_text("",1)
        display_centered_text("",2)
        display_centered_text("History",3)
        display_centered_text("Not Found!",4)
        oled.show()
        history_showed = True
    else:
        oled.fill(0)
        line_gap = 10
        for i in range(len(history_array)):
            oled.text(generate_selection_line(f"{i+1}.History ({history_array[i].get_calculation_type()})", i==pointer), 0, line_gap*i)
        oled.show()



def generate_selection_line(text, is_selected):
    led_line = "" #blank string
    
    if is_selected:
        led_line += "["
    else:
        led_line += " "
            
    led_line +=  text
    
    if is_selected:
        led_line += " ]"
        
    return led_line

def display_centered_text(text, line):
    # Calculate text position
    text_width = len(text) * 8  # Each character is 8 pixels wide for the default font
    x = (oled_width - text_width) // 2
    y = (line-1)*10  

    # Display text
    oled.text(text, x, y, 1)


def display_text(text, line):
    # Calculate text position
    x = 1
    y = (line-1)*10

    # Display text
    oled.text(text, x, y, 1)


def open_menu():
    # Clear the display
    oled.fill(0)
    
    line_gap = 18
    oled.text(generate_selection_line("1. Measure HR", selected==0), 0, 0)
    oled.text(generate_selection_line("2. Basic HRV", selected==1), 0, line_gap*1)
    oled.text(generate_selection_line("3. Kubios", selected==2), 0, line_gap*2)
    oled.text(generate_selection_line("4. History", selected==3), 0, line_gap*3)
    
    oled.show()

############ Operation IO variables ######
button = Pin(12, mode = Pin.IN, pull = Pin.PULL_UP)
rot = Encoder(10, 11)
selected = 0
history_selected = 0
operation_status = 0
HR_measure_started = False
button_pre_val = 1

##########################################

#################################
data = DataAdapter()
#data = DataAdapter(file_path)

history_showed = False
while True:

    if operation_status == 0:
        open_menu()
    elif operation_status == 1:
        operation_1_HR()
    elif operation_status == 2:
        operation_2_3_HRV(False)
    elif operation_status == 3:
        operation_2_3_HRV(True)
    elif operation_status == 4:
        if history_showed == False:
            operation_3_History(history_selected)


    #--- Only for changing selection internally. In the print section it will be used to show the selection in LED
    while rot.fifo.has_data():
        rotation = rot.fifo.get()
        if operation_status==0 :
            selected = selected + rotation
            if selected < 0:
                selected = 0
            if selected > 3:
                selected = 3
        if operation_status==4 :
            history_selected = history_selected +  rotation

            if  history_selected < 0:
                history_selected = 0
                
            if history_selected > len(history_array)-1:
                history_selected = len(history_array)-1
    
    button_val = button.value()

    #---- Only for turning on the LED of and on and Changing the Led_status OFF and ON for display in next cycle
    if button_pre_val ==0 and button_val==1:
        button_pre_val = button_val
        
        if operation_status == 0:
            if selected == 0:
                operation_status = 1
                HR_measure_started = False
                continue
            elif selected == 1:
                operation_status = 2
                current_time = 0
                calculation_frame = []
                HRV_calculated = False
                continue
            elif selected == 2:
                operation_status = 3
                current_time = 0
                calculation_frame = []
                HRV_calculated = False
                continue
            elif selected == 3:
                operation_status = 4
                history_selected = 0
                history_showed = False
                continue
    
        if operation_status == 1:
            if HR_measure_started == False:
                HR_measure_started = True
                oled.fill(0)
            else:
                operation_status = 0
            continue
        elif operation_status == 2 or operation_status == 3:
            if HRV_calculated == True:
                operation_status = 0
                continue
        elif operation_status == 4:
            if history_showed == False:
                if len(history_array) > 0:
                    print_hrv(history_array[history_selected])
                    history_showed = True
                    continue
            else:
                operation_status = 0
                continue
        
    button_pre_val = button_val

   