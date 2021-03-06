"""
Flight simulator
    Pod sends current state and variables each loop.  sim() returns new
    values for this data based on pod's current state.

    Does not currently feature protections against re-using Reservoir air charges.
"""

#from time import clock
import random, numpy


def sim(PodStatus):

    print("In Flight Simulation")

    # Evaluate HV status
    if (PodStatus.cmd_int['HV'] == 1):
        PodStatus.sensor_data['SD_HVBusData_BusVoltage'] = 500
    else:
        PodStatus.sensor_data['SD_HVBusData_BusVoltage'] = 0
    if PodStatus.HV == True:
        PodStatus.sensor_data['SD_HVBusData_MotorCurrent'] = PodStatus.throttle * 340
    else:
        PodStatus.sensor_data['SD_HVBusData_MotorCurrent'] = 0

    # Activate Res1
    if (PodStatus.cmd_int['Res1_Sol'] == 1) and (PodStatus.Vent_Sol == 1):
        print('FS: Pressurizing Brakes from Res1')
        PodStatus.sensor_data['Brake_Pressure'] = 200 + random.randint(-10,10)*10**-2

    # Activate Res2
    if (PodStatus.cmd_int['Res2_Sol'] == 1) and (PodStatus.Vent_Sol == 1):
        print('FS: Pressurizing Brakes from Res2')
        PodStatus.sensor_data['Brake_Pressure'] = 200 + random.randint(-10,10)*10**-2

    # Activate Vent
    if (PodStatus.cmd_int['Vent_Sol'] == 0):
        print('FS: Venting Brake Pressure')
        PodStatus.sensor_data['Brake_Pressure'] = 0.01 + random.randint(-10,10)*10**-3

    if PodStatus.Brakes is False:

        # Increment accelerometer data
        PodStatus.sensor_data['IMU1_Z'] = PodStatus.throttle * 0.7 * (1 - PodStatus.true_data['V']['val']/300*0.2) + random.randint(-1,1)*10**-2 - 0.05
        PodStatus.sensor_data['IMU2_Z'] = PodStatus.throttle * 0.7 * (1 - PodStatus.true_data['V']['val']/300*0.2) + random.randint(-1,1)*10**-2 - 0.05

        print('IMU1_Z: ' + str(PodStatus.sensor_data['IMU1_Z']))
        print('IMU2_Z: ' + str(PodStatus.sensor_data['IMU2_Z']))

    if PodStatus.Brakes is True and PodStatus.true_data['V']['val'] > 0:

        # Increment accelerometer data
        PodStatus.sensor_data['IMU1_Z'] = -5 - random.randint(-1,1)*10**-2
        PodStatus.sensor_data['IMU2_Z'] = -5 - random.randint(-1,1)*10**-2
        print('IMU1_Z: ' + str(PodStatus.sensor_data['IMU1_Z']))
        print('IMU2_Z: ' + str(PodStatus.sensor_data['IMU2_Z']))

    # Increment motor resolver data
    PodStatus.sensor_data['SD_MotorData_MotorRPM'] = PodStatus.sensor_data['SD_MotorData_MotorRPM'] + \
                                                     (PodStatus.true_data['A'][
                                                          'val'] * 32.174 * PodStatus.poll_interval + \
                                                      random.randint(-1, 1) * 10 ** -2) * 60 / PodStatus.wheel_circum
    if PodStatus.sensor_data['SD_MotorData_MotorRPM'] < 0: PodStatus.sensor_data['SD_MotorData_MotorRPM'] = 0

    if ((PodStatus.true_data['D']['val']/100 - PodStatus.stripe_count) > 25) and \
            (abs(PodStatus.true_data['D']['val']/100 - numpy.around(PodStatus.true_data['D']['val']/100)) < 0.05):
        PodStatus.sensor_data['LST_Right'] += 1
        PodStatus.sensor_data['LST_Left'] += 1

    print("Left Stripe:" + str(PodStatus.sensor_data['LST_Left']) + '\t' + "Right Stripe:" + str(PodStatus.sensor_data['LST_Right']))

    return(PodStatus)


