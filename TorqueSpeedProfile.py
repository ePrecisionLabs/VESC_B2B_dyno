from datetime import datetime
import json
from pyvesc import VESC
import math
import time


# Adjust here the name of the COM port for each motor and the log file name
config_file_name = 'config_torque_speed_profile.json'
log_file_name = 'dut_log_profile'


# Helper functions
def load_config(config_file):
    with open(config_file, "r") as file:
        return json.load(file)

def do_rpm_ramp(motor, start_rpm, end_rpm, settling_time_s, max_ramp_step):
    rpm = start_rpm
    nb_steps = math.ceil(abs(end_rpm-start_rpm)/max_ramp_step)
    for _ in range(nb_steps):
        rpm = rpm + (end_rpm-start_rpm)/nb_steps
        motor.set_rpm(int(rpm))
        time.sleep(settling_time_s)

def do_current_ramp(motor, start_current, end_current, settling_time_s, max_ramp_step):
    current = start_current
    nb_steps = math.ceil(abs(end_current-start_current)/max_ramp_step)
    for _ in range(nb_steps):
        current = current + (end_current-start_current)/nb_steps
        motor.set_current(current)
        time.sleep(settling_time_s)

def log_measurements_to_file(measurements, log_file):
    log_file.write(f'\
            {measurements.time_ms},\
            {measurements.rpm},\
            {measurements.duty_cycle_now},\
            {measurements.v_in},\
            {measurements.avg_motor_current},\
            {measurements.avg_input_current},\
            {measurements.temp_fet},\
            {measurements.temp_motor}\n')


# Main test loop
def run_b2b_dyno_test(config):
    motor_dut_port = config['motor_dut_port']
    motor_absorber_port = config['motor_absorber_port']
    rpm_array = config['rpm_array']
    current_array = config['current_array']
    duration_array = config['duration_array']
    time_btwn_measurements = config['time_btwn_measurements']
    ramp_settling_time_s = config['ramp_settling_time_s']
    max_rpm_ramp_step = config['max_rpm_ramp_step']
    max_current_ramp_step = config['max_current_ramp_step']

    last_rpm = 0
    last_current = 0
    isFaulted = False
    log_file_name_ext = log_file_name + datetime.now().strftime("_%Y%m%d_%H%M%S") + '.txt'

    with open(log_file_name_ext, "w") as log_file:
        with VESC(serial_port=motor_dut_port) as motor_dut:
            with VESC(serial_port=motor_absorber_port) as motor_absorber:

                log_file.write(f"Torque-Speed profile script\n")
                log_file.write(f"DUT Firmware: {motor_dut.get_firmware_version()}\n")
                log_file.write(f"Absorber Firmware: {motor_absorber.get_firmware_version()}\n")
                log_file.write(f'time_ms, rpm, duty_cycle, v_in, avg_motor_current, avg_input_current, temp_fet, temp_motor\n')

                for idx, rpm in rpm_array:
                    current = current_array[idx]
                    duration = duration_array[idx]

                    do_rpm_ramp(motor_absorber, last_rpm, rpm, ramp_settling_time_s, max_rpm_ramp_step)
                    do_current_ramp(motor_dut, last_current, current, ramp_settling_time_s, max_current_ramp_step)

                    nb_captures = int(duration / time_btwn_measurements)
                    for _ in range(nb_captures):
                        measurements_dut = motor_dut.get_measurements()
                        if measurements_dut is None:
                            log_file.write('Communication error with DUT - received None\n')
                        else:
                            log_measurements_to_file(measurements_dut, log_file)
                            if measurements_dut.mc_fault_code != b'\x00':
                                log_file.write(f'DUT faulted with code {measurements_dut.mc_fault_code}\n')
                                isFaulted = True
                                break

                        measurements_abs = motor_absorber.get_measurements()
                        if measurements_abs is None:
                            log_file.write('Communication error with Absorber - received None\n')
                        else:
                            if measurements_abs.mc_fault_code != b'\x00':
                                log_file.write(f'Absorber faulted with code {measurements_abs.mc_fault_code}\n')
                                isFaulted = True
                                break

                        time.sleep(time_btwn_measurements)

                    last_rpm = rpm
                    last_current = current
                    do_current_ramp(motor_dut, last_current, 0, ramp_settling_time_s, last_current)

                    if isFaulted:
                        break

                do_rpm_ramp(motor_absorber, last_rpm, 0, ramp_settling_time_s, max_rpm_ramp_step)
                log_file.write('End of test sequence\n')


if __name__ == "__main__":
    config = load_config(config_file_name)
    run_b2b_dyno_test(config)