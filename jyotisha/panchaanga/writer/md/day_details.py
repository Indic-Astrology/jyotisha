#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import os
import os.path
import sys
from datetime import timedelta
from io import StringIO
from math import ceil

from icalendar import Calendar, Event, Alarm
from indic_transliteration import xsanscript as sanscript

import jyotisha
import jyotisha.custom_transliteration
import jyotisha.names
import jyotisha.panchaanga.spatio_temporal.annual
import jyotisha.panchaanga.temporal
from jyotisha import names
from jyotisha.names import translate_and_transliterate
from jyotisha.panchaanga.spatio_temporal import City
from jyotisha.panchaanga.temporal import AngaType
from jyotisha.panchaanga.temporal.festival.rules import RulesRepo
from jyotisha.panchaanga.temporal.time import Hour
from jyotisha.panchaanga.writer.ics import util

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s  %(filename)s:%(lineno)d : %(message)s "
)

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def write_to_file(ics_calendar, fname):
  ics_calendar_file = open(fname, 'wb')
  ics_calendar_file.write(ics_calendar.to_ical())
  ics_calendar_file.close()


def writeDailyICS(panchaanga, script=sanscript.DEVANAGARI):
  """Write out the panchaanga TeX using a specified template
  """
  compute_lagnams=panchaanga.computation_system.options.set_lagnas

  samvatsara_id = (panchaanga.year - 1568) % 60 + 1  # distance from prabhava
  samvatsara_names = (jyotisha.names.NAMES['SAMVATSARA_NAMES'][script][samvatsara_id],
                      jyotisha.names.NAMES['SAMVATSARA_NAMES'][script][(samvatsara_id % 60) + 1])

  yname_solar = samvatsara_names[0]  # Assign year name until Mesha Sankranti
  yname_lunar = samvatsara_names[0]  # Assign year name until Mesha Sankranti


  ics_calendar = Calendar()

  alarm = Alarm()
  alarm.add('action', 'DISPLAY')
  alarm.add('trigger', timedelta(hours=-4))  # default alarm, with a 4 hour reminder

  daily_panchaangas = panchaanga.daily_panchaangas_sorted()
  for d, daily_panchaanga in enumerate(daily_panchaangas):
    if daily_panchaanga.date < panchaanga.start_date or daily_panchaanga.date > panchaanga.end_date:
      continue

    if daily_panchaanga.solar_sidereal_date_sunset.month == 1:
      # Flip the year name for the remaining days
      yname_solar = samvatsara_names[1]
    if daily_panchaanga.lunar_month_sunrise.index == 1:
      # Flip the year name for the remaining days
      yname_lunar = samvatsara_names[1]

    event = get_day_summary_event(d, panchaanga, script)

    ics_calendar.add_component(event)

  return ics_calendar


def get_day_summary_event(d, panchaanga, script):
  daily_panchaanga = panchaanga.daily_panchaangas_sorted()[d]
  event = Event()
  (title, details) = day_summary(d=d, panchaanga=panchaanga, script=script)
  event.add('summary', title)
  event.add('description', details)
  tz = daily_panchaanga.city.get_timezone_obj()
  dt_start = tz.julian_day_to_local_datetime(jd=daily_panchaanga.jd_sunrise)
  event.add('dtstart', dt_start)
  event.add('dtend', tz.julian_day_to_local_datetime(jd=daily_panchaanga.jd_next_sunrise))
  event.add_component(util.get_4_hr_display_alarm())
  event['X-MICROSOFT-CDO-ALLDAYEVENT'] = 'TRUE'
  event['TRANSP'] = 'TRANSPARENT'
  event['X-MICROSOFT-CDO-BUSYSTATUS'] = 'FREE'
  return event


def day_summary(d, panchaanga, script):
  daily_panchaanga = panchaanga.daily_panchaangas_sorted()[d]
  lunar_month_str = names.get_chandra_masa(month=daily_panchaanga.lunar_month_sunrise.index, script=script)
  solar_month_str = names.NAMES['RASHI_NAMES'][script][daily_panchaanga.solar_sidereal_date_sunset.month]
  tropical_month_str = names.NAMES['RTU_MASA_NAMES_SHORT'][script][daily_panchaanga.tropical_date_sunset.month]
  lunar_position = "%s-%s" % (jyotisha.names.NAMES['RASHI_NAMES'][script][daily_panchaanga.sunrise_day_angas.raashis_with_ends[0].anga.index], jyotisha.names.NAMES['NAKSHATRA_NAMES'][script][daily_panchaanga.sunrise_day_angas.nakshatras_with_ends[0].anga.index])
  title = '%s-%s,%s🌛🌌◢◣%s-%s🌌🌞◢◣%s-%s🪐🌞' % (
    lunar_month_str, str(daily_panchaanga.get_date(month_type=RulesRepo.LUNAR_MONTH_DIR)), lunar_position,
    solar_month_str, str(daily_panchaanga.solar_sidereal_date_sunset), tropical_month_str,
    str(daily_panchaanga.tropical_date_sunset))

  output_stream = StringIO()
  tithi_data_str = daily_panchaanga.sunrise_day_angas.get_anga_data_str(anga_type=AngaType.TITHI, script=script, reference_jd=daily_panchaanga.julian_day_start)
  nakshatra_data_str = daily_panchaanga.sunrise_day_angas.get_anga_data_str(anga_type=AngaType.NAKSHATRA, script=script, reference_jd=daily_panchaanga.julian_day_start)
  chandrashtama_rashi_data_str, rashi_data_str = get_raashi_data_str(daily_panchaanga, script)
  yoga_data_str = daily_panchaanga.sunrise_day_angas.get_anga_data_str(anga_type=AngaType.YOGA, script=script, reference_jd=daily_panchaanga.julian_day_start)
  karana_data_str = daily_panchaanga.sunrise_day_angas.get_anga_data_str(anga_type=AngaType.KARANA, script=script, reference_jd=daily_panchaanga.julian_day_start)
  tz = daily_panchaanga.city.get_timezone_obj()
  # braahma = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.braahma.jd_start - jd)).toString()
  # praatahsandhya = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.praatas_sandhyaa.jd_start - jd)).toString()
  # praatahsandhya_end = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.praatas_sandhyaa_end.jd_start - jd)).toString()
  # saangava = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.saangava.jd_start - jd)).toString()
  # madhyaahna = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.madhyaahna.jd_start - jd)).toString()
  # madhyahnika_sandhya = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.maadhyaahnika_sandhyaa.jd_start - jd)).toString()
  # madhyahnika_sandhya_end = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.maadhyaahnika_sandhyaa_end.jd_start - jd)).toString()
  aparaahna = tz.julian_day_to_local_time(daily_panchaanga.day_length_based_periods.aparaahna.jd_start).get_hour_str()
  sayahna = tz.julian_day_to_local_time(daily_panchaanga.day_length_based_periods.saayaahna.jd_start).get_hour_str()

  # sayamsandhya = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.saayam_sandhyaa.jd_start - jd)).toString()
  # sayamsandhya_end = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.saayam_sandhyaa_end.jd_start - jd)).toString()
  # ratriyama1 = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.raatri_yaama_1.jd_start - jd)).toString()
  # sayana_time = jyotisha.panchaanga.temporal.Time(24 * (daily_panchaanga.day_length_based_periods.shayana.jd_start - jd)).toString()
  # Assign samvatsara, ayana, rtu #
  ayanam_sidereal = jyotisha.names.NAMES['AYANA_NAMES'][script][daily_panchaanga.solar_sidereal_date_sunset.month]
  ayanam = jyotisha.names.NAMES['AYANA_NAMES'][script][daily_panchaanga.tropical_date_sunset.month]
  rtu_solar = jyotisha.names.NAMES['RTU_NAMES'][script][daily_panchaanga.solar_sidereal_date_sunset.month]
  rtu_tropical = jyotisha.names.NAMES['RTU_NAMES'][script][daily_panchaanga.tropical_date_sunset.month]
  rtu_lunar = jyotisha.names.NAMES['RTU_NAMES'][script][int(ceil(daily_panchaanga.lunar_month_sunrise.index))]

  month_end_str = ''
  if daily_panchaanga.solar_sidereal_date_sunset.month_transition is None:
    month_end_str = ''
  # TODO: Fix and enable below.
  # else:
  #   _m = daily_panchaangas[d - 1].solar_sidereal_date_sunset.month
  #   if daily_panchaanga.solar_sidereal_date_sunset.month_transition >= daily_panchaanga.jd_next_sunrise:
  #     month_end_str = '%s►%s' % (jyotisha.names.NAMES['RASHI_NAMES'][language][_m],
  #                                Hour(24 * (
  #                                    daily_panchaanga.solar_sidereal_date_sunset.month_transition - daily_panchaanga.julian_day_start + 1)).toString(
  #                                ))
  #   else:
  #     month_end_str = '%s►%s' % (jyotisha.names.NAMES['RASHI_NAMES'][language][_m],
  #                                Hour(
  #                                  24 * (
  #                                        daily_panchaanga.solar_sidereal_date_sunset.month_transition - daily_panchaanga.julian_day_start)).toString(
  #                                ))
  if month_end_str == '':
    month_data = '%s (%s %d)' % (
      jyotisha.names.NAMES['RASHI_NAMES'][script][daily_panchaanga.solar_sidereal_date_sunset.month],
      translate_and_transliterate('dinaM', script), daily_panchaanga.solar_sidereal_date_sunset.day)
  else:
    month_data = '%s (%s %d); %s' % (
      jyotisha.names.NAMES['RASHI_NAMES'][script][daily_panchaanga.solar_sidereal_date_sunset.month],
      translate_and_transliterate('dinaM', script), daily_panchaanga.solar_sidereal_date_sunset.day, month_end_str)
  # TODO: renable below and related code further down (look for yname_lunar)
  # if yname_lunar == yname_solar:
  #   print('*' + getName('saMvatsaraH', language) + '*—%s' % yname_lunar, file=output_stream)
  #   print('*' + getName('ayanam', language) + '*—%s' % ayanam, file=output_stream)
  print("___________________", file=output_stream)
  print('- 🪐🌞**%s** — %s %s' % (translate_and_transliterate('sAyanamAnam', script), rtu_tropical, ayanam), file=output_stream)
  print('- 🌌🌞**%s** — %s %s' % (translate_and_transliterate('sauramAnam', script), rtu_solar, ayanam_sidereal), file=output_stream)
  print('- 🌛**%s** — %s %s' % (translate_and_transliterate('cAndramAnam', script), rtu_lunar, lunar_month_str), file=output_stream)
  # if yname_lunar != yname_solar:
  #   print('*' + getName('saMvatsaraH', language) + '*—%s' % yname_solar, file=output_stream)
  #   print('*' + getName('ayanam', language) + '*—%s' % ayanam, file=output_stream)
  # if yname_lunar != yname_solar:
  #   print('*' + getName('saMvatsaraH', language) + '*—%s' % yname_lunar, file=output_stream)
  #   print('*' + getName('ayanam', language) + '*—%s' % ayanam, file=output_stream)
  print("___________________", file=output_stream)
  # braahma
  # praatahsandhya, praatahsandhya_end
  # saangava
  # madhyahnika_sandhya, madhyahnika_sandhya_end
  # madhyaahna
  # aparaahna
  # sayahna
  # sayamsandhya, sayamsandhya_end
  # dinaanta
  print('- 🌛%s  ' % (tithi_data_str), file=output_stream)
  vara = jyotisha.names.NAMES['VARA_NAMES'][script][daily_panchaanga.date.get_weekday()]
  print('- **%s**—%s  ' % (translate_and_transliterate('vAsaraH', script), vara), file=output_stream)
  print('- 🌛%s (%s)  ' % (nakshatra_data_str, rashi_data_str), file=output_stream)
  print("___________________", file=output_stream)
  print('- 🌛🌞%s  ' % (yoga_data_str), file=output_stream)
  print('- 🌛🌞%s  ' % (karana_data_str), file=output_stream)
  print('- 🌛%s  ' % (chandrashtama_rashi_data_str), file=output_stream)
  print("___________________", file=output_stream)
  print('- 🌏**%s** (%s)  ' % (
    translate_and_transliterate('kSEtram', script), jyotisha.custom_transliteration.tr(panchaanga.city.name, script)),
        file=output_stream)
  add_sun_moon_rise_info(daily_panchaanga, output_stream, script)

  if panchaanga.computation_system.options.set_lagnas:
    lagna_data_str = get_lagna_data_str(daily_panchaanga, script)
    print('- %s  ' % (lagna_data_str), file=output_stream)


  print("___________________", file=output_stream)
  print('- 🌞️🏄**%s**—%s►%s  ' % (translate_and_transliterate('aparAhNa-muhUrtaH', script), aparaahna, sayahna), file=output_stream)
  dinaanta = tz.julian_day_to_local_time(daily_panchaanga.day_length_based_periods.dinaanta.jd_start).get_hour_str()
  print('- **%s**—%s  ' % (translate_and_transliterate('dinAntaH', script), dinaanta), file=output_stream)
  print("___________________", file=output_stream)

  add_raahu_yama_gulika_info(daily_panchaanga, output_stream, script)

  print("___________________", file=output_stream)
  add_shuula_info(daily_panchaanga, output_stream, script)
  print("___________________", file=output_stream)

  output_text = output_stream.getvalue()
  return (title, output_text)


def add_raahu_yama_gulika_info(daily_panchaanga, output_stream, script):
  tz = daily_panchaanga.city.get_timezone_obj()
  rahu = daily_panchaanga.day_length_based_periods.raahu.to_hour_string(tz=tz)
  yama = daily_panchaanga.day_length_based_periods.yama.to_hour_string(tz=tz)
  gulika = daily_panchaanga.day_length_based_periods.gulika.to_hour_string(tz=tz)
  print('- **%s**—%s; **%s**—%s; **%s**—%s  ' % (translate_and_transliterate('rAhukAlaH', script), rahu,
                                         translate_and_transliterate('yamaghaNTaH', script), yama,
                                         translate_and_transliterate('gulikakAlaH', script), gulika),
        file=output_stream)


def add_shuula_info(daily_panchaanga, output_stream, script):
  tz = daily_panchaanga.city.get_timezone_obj()
  shulam_end_jd = daily_panchaanga.jd_sunrise + (daily_panchaanga.jd_sunset - daily_panchaanga.jd_sunrise) * (
      names.SHULAM[daily_panchaanga.date.get_weekday()][1] / 30)
  print('- **%s**—%s (►%s); **%s**–%s  ' % (
    translate_and_transliterate('zUlam', script),
    translate_and_transliterate(names.SHULAM[daily_panchaanga.date.get_weekday()][0], script),
    tz.julian_day_to_local_time(shulam_end_jd).get_hour_str(),
    translate_and_transliterate('parihAraH', script),
    translate_and_transliterate(names.SHULAM[daily_panchaanga.date.get_weekday()][2], script)),
        file=output_stream)


def add_sun_moon_rise_info(daily_panchaanga, output_stream, script):
  tz = daily_panchaanga.city.get_timezone_obj()
  # We prefer using Hour() below so as to differentiate post-midnight times.
  moonrise = tz.julian_day_to_local_time(daily_panchaanga.jd_moonrise).get_hour_str(reference_date=daily_panchaanga.date)
  moonset = tz.julian_day_to_local_time(daily_panchaanga.jd_moonset).get_hour_str(reference_date=daily_panchaanga.date)
  if daily_panchaanga.jd_moonrise > daily_panchaanga.jd_next_sunrise:
    moonrise = '---'
  if daily_panchaanga.jd_moonset > daily_panchaanga.jd_next_sunrise:
    moonset = '---'

  sunrise = tz.julian_day_to_local_time(daily_panchaanga.jd_sunrise).get_hour_str()
  sunset = tz.julian_day_to_local_time(daily_panchaanga.jd_sunset).get_hour_str()
  midday = tz.julian_day_to_local_time(daily_panchaanga.day_length_based_periods.aparaahna.jd_start).get_hour_str()
  print('- 🌅**%s**—%s-%s🌞️-%s🌇  ' % (translate_and_transliterate('sUryOdayaH', script),
    sunrise, midday,
    sunset),
        file=output_stream)
  if daily_panchaanga.jd_moonrise < daily_panchaanga.jd_moonset:
    print('- 🌛**%s**—%s; **%s**—%s  ' % (
      translate_and_transliterate('candrOdayaH', script), moonrise,
      translate_and_transliterate('candrAstamayaH', script), moonset),
          file=output_stream)
  else:
    print('- 🌛**%s**—%s; **%s**—%s  ' % (
      translate_and_transliterate('candrAstamayaH', script), moonset,
      translate_and_transliterate('candrOdayaH', script), moonrise),
          file=output_stream)


def get_raashi_data_str(daily_panchaanga, script):
  jd = daily_panchaanga.julian_day_start
  chandrashtama_rashi_data_str = ''
  for raashi_span in daily_panchaanga.sunrise_day_angas.raashis_with_ends:
    (rashi_ID, rashi_end_jd) = (raashi_span.anga.index, raashi_span.jd_end)
    rashi = jyotisha.names.NAMES['RASHI_NAMES'][script][rashi_ID]
    if rashi_end_jd is None:
      rashi_data_str = '%s' % (rashi)
      chandrashtama_rashi_data_str = '- **%s**—%s' % (translate_and_transliterate('candrASTama-rAziH', script), 
        jyotisha.names.NAMES['RASHI_NAMES'][script][((rashi_ID - 8) % 12) + 1])
    else:
      rashi_data_str = '%s►%s' % (
        rashi, Hour(24 * (rashi_end_jd - jd)).to_string())
      chandrashtama_rashi_data_str = '- **%s**—%s►%s; %s ➥' % (
        translate_and_transliterate('candrASTama-rAziH', script),
        jyotisha.names.NAMES['RASHI_NAMES'][script][((rashi_ID - 8) % 12) + 1],
        Hour(24 * (rashi_end_jd - jd)).to_string(),
        jyotisha.names.NAMES['RASHI_NAMES'][script][((rashi_ID - 7) % 12) + 1])
  return chandrashtama_rashi_data_str, rashi_data_str


def get_lagna_data_str(daily_panchaanga, script):
  jd = daily_panchaanga.julian_day_start
  lagna_data_str = ''
  for lagna_ID, lagna_end_jd in daily_panchaanga.lagna_data:
    lagna = jyotisha.names.NAMES['RASHI_NAMES'][script][lagna_ID]
    lagna_data_str = '%s; %s►%s' % \
                     (lagna_data_str, lagna,
                      Hour(24 * (lagna_end_jd - jd)).to_string(
                      ))
  lagna_data_str = '*' + translate_and_transliterate('lagnam', script) + '*—' + lagna_data_str[2:]
  return lagna_data_str




def main():
  [city_name, latitude, longitude, tz] = sys.argv[1:5]
  year = int(sys.argv[5])

  compute_lagnams = False  # Default
  script = sanscript.DEVANAGARI  # Default language is devanagari
  fmt = 'hh:mm'

  if len(sys.argv) == 9:
    compute_lagnams = True
    fmt = sys.argv[7]
    script = sys.argv[6]
  elif len(sys.argv) == 8:
    script = sys.argv[6]
    fmt = sys.argv[7]
    compute_lagnams = False
  elif len(sys.argv) == 7:
    script = sys.argv[6]
    compute_lagnams = False

  city = City(city_name, latitude, longitude, tz)

  panchaanga = jyotisha.panchaanga.spatio_temporal.annual.get_panchaanga_for_civil_year(city=city, year=year)

  panchaanga.update_festival_details()

  ics_calendar = writeDailyICS(panchaanga)
  city_name_en = jyotisha.custom_transliteration.romanise(
    jyotisha.custom_transliteration.tr(city.name, sanscript.IAST)).title()
  output_file = os.path.expanduser('%s/%s-%d-%s-daily.ics' % ("../ics/daily", city_name_en, year, script))
  write_to_file(ics_calendar, output_file)
  print('Output ICS written to %s' % output_file, file=sys.stderr)


if __name__ == '__main__':
  main()
