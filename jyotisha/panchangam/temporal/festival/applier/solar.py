from datetime import datetime
from math import floor

from pytz import timezone as tz

from jyotisha import names
from jyotisha.panchangam import temporal
from jyotisha.panchangam.temporal import zodiac
from jyotisha.panchangam.temporal.body import Graha
from jyotisha.panchangam.temporal.festival.applier import FestivalAssigner
from jyotisha.panchangam.temporal.hour import Hour
from jyotisha.panchangam.temporal.zodiac import NakshatraDivision, AngaSpan


class SolarFestivalAssigner(FestivalAssigner):
  def assign_all(self, debug_festivals=False):
    self.assign_gajachhaya_yoga(debug_festivals=debug_festivals)
    self.assign_mahodaya_ardhodaya(debug_festivals=debug_festivals)
    self.assign_month_day_festivals(debug_festivals=debug_festivals)
    self.assign_ayanam(debug_festivals=debug_festivals)
    self.assign_vishesha_vyatipata(debug_festivals=debug_festivals)

  def assign_ayanam(self, debug_festivals=False):
    last_d_assigned = 0
    for d in range(1, self.panchaanga.duration + 1):

      [y, m, dt, t] = temporal.jd_to_utc_gregorian(self.panchaanga.jd_start_utc + d - 1)

      # checking @ 6am local - can we do any better?
      local_time = tz(self.panchaanga.city.timezone).localize(datetime(y, m, dt, 6, 0, 0))
      # compute offset from UTC in hours
      tz_off = (datetime.utcoffset(local_time).days * 86400 +
                datetime.utcoffset(local_time).seconds) / 3600.0

      # TROPICAL AYANAMS
      if self.panchaanga.solar_month_day[d] == 1:
        ayana_jd_start = \
          Graha(Graha.SUN).get_next_raashi_transit(jd_start=self.panchaanga.jd_sunrise[d],
                                                   jd_end=self.panchaanga.jd_sunrise[d] + 15,
                                                   ayanamsha_id=zodiac.Ayanamsha.ASHVINI_STARTING_0)[0][0]
        [_y, _m, _d, _t] = temporal.jd_to_utc_gregorian(ayana_jd_start + (tz_off / 24.0))
        # Reduce fday by 1 if ayana time precedes sunrise and change increment _t by 24
        fday_nirayana = int(temporal.utc_gregorian_to_jd(_y, _m, _d, 0) - self.panchaanga.jd_start_utc + 1)
        if fday_nirayana > self.panchaanga.duration:
          continue
        if ayana_jd_start < self.panchaanga.jd_sunrise[fday_nirayana]:
          fday_nirayana -= 1
          _t += 24
        ayana_time = Hour(_t).toString(format=self.panchaanga.fmt)

        self.panchaanga.festivals[fday_nirayana].append('%s\\textsf{%s}{\\RIGHTarrow}\\textsf{%s}' % (
          names.NAMES['RTU_MASA_NAMES'][self.panchaanga.script][self.panchaanga.solar_month[d]], '', ayana_time))
        self.panchaanga.tropical_month_end_time[fday_nirayana] = ayana_jd_start
        for i in range(last_d_assigned + 1, fday_nirayana + 1):
          self.panchaanga.tropical_month[i] = self.panchaanga.solar_month[d]
        last_d_assigned = fday_nirayana
        if self.panchaanga.solar_month[d] == 3:
          if self.panchaanga.jd_sunset[fday_nirayana] < ayana_jd_start < self.panchaanga.jd_sunset[fday_nirayana + 1]:
            self.panchaanga.festivals[fday_nirayana].append('dakSiNAyana-puNyakAlaH')
          else:
            self.panchaanga.festivals[fday_nirayana - 1].append('dakSiNAyana-puNyakAlaH')
        if self.panchaanga.solar_month[d] == 9:
          if self.panchaanga.jd_sunset[fday_nirayana] < ayana_jd_start < self.panchaanga.jd_sunset[fday_nirayana + 1]:
            self.panchaanga.festivals[fday_nirayana + 1].append('uttarAyaNa-puNyakAlaH/mitrOtsavaH')
          else:
            self.panchaanga.festivals[fday_nirayana].append('uttarAyaNa-puNyakAlaH/mitrOtsavaH')
    for i in range(last_d_assigned + 1, self.panchaanga.duration + 1):
      self.panchaanga.tropical_month[i] = (self.panchaanga.solar_month[last_d_assigned] % 12) + 1

  def assign_month_day_festivals(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = temporal.jd_to_utc_gregorian(self.panchaanga.jd_start_utc + d - 1)
      ####################
      # Festival details #
      ####################

      # KARADAIYAN NOMBU
      if self.panchaanga.solar_month[d] == 12 and self.panchaanga.solar_month_day[d] == 1:
        if NakshatraDivision(self.panchaanga.jd_sunrise[d] - (1 / 15.0) * (self.panchaanga.jd_sunrise[d] - self.panchaanga.jd_sunrise[d - 1]),
                             ayanamsha_id=self.panchaanga.ayanamsha_id).get_solar_rashi() == 12:
          # If kumbha prevails two ghatikAs before sunrise, nombu can be done in the early morning itself, else, previous night.
          self.panchaanga.fest_days['ta:kAraDaiyAn2 nOn2bu'] = [d - 1]
        else:
          self.panchaanga.fest_days['ta:kAraDaiyAn2 nOn2bu'] = [d]

      # KUCHELA DINAM
      if self.panchaanga.solar_month[d] == 9 and self.panchaanga.solar_month_day[d] <= 7 and self.panchaanga.weekday[d] == 3:
        self.panchaanga.fest_days['kucEla-dinam'] = [d]

      # MESHA SANKRANTI
      if self.panchaanga.solar_month[d] == 1 and self.panchaanga.solar_month[d - 1] == 12:
        # distance from prabhava
        samvatsara_id = (y - 1568) % 60 + 1
        new_yr = 'mESa-saGkrAntiH' + '~(' + names.NAMES['SAMVATSARA_NAMES']['hk'][
          (samvatsara_id % 60) + 1] + \
                 '-' + 'saMvatsaraH' + ')'
        # self.panchaanga.fest_days[new_yr] = [d]
        self.add_festival(new_yr, d, debug_festivals)
        self.add_festival('paJcAGga-paThanam', d, debug_festivals)

  def assign_vishesha_vyatipata(self, debug_festivals=False):
    vs_list = self.panchaanga.fest_days['vyatIpAta-zrAddham']
    for d in vs_list:
      if self.panchaanga.solar_month[d] == 9:
        self.panchaanga.fest_days['vyatIpAta-zrAddham'].remove(d)
        festival_name = 'mahAdhanurvyatIpAta-zrAddham'
        self.add_festival(festival_name, d, debug_festivals)
      elif self.panchaanga.solar_month[d] == 6:
        self.panchaanga.fest_days['vyatIpAta-zrAddham'].remove(d)
        festival_name = 'mahAvyatIpAta-zrAddham'
        self.add_festival(festival_name, d, debug_festivals)

  def assign_gajachhaya_yoga(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = temporal.jd_to_utc_gregorian(self.panchaanga.jd_start_utc + d - 1)

      # checking @ 6am local - can we do any better?
      local_time = tz(self.panchaanga.city.timezone).localize(datetime(y, m, dt, 6, 0, 0))
      # compute offset from UTC in hours
      tz_off = (datetime.utcoffset(local_time).days * 86400 +
                datetime.utcoffset(local_time).seconds) / 3600.0
      # GAJACHHAYA YOGA
      if self.panchaanga.solar_month[d] == 6 and self.panchaanga.solar_month_day[d] == 1:
        moon_magha_jd_start = moon_magha_jd_start = t28_start = None
        moon_magha_jd_end = moon_magha_jd_end = t28_end = None
        moon_hasta_jd_start = moon_hasta_jd_start = t30_start = None
        moon_hasta_jd_end = moon_hasta_jd_end = t30_end = None

        sun_hasta_jd_start, sun_hasta_jd_end = AngaSpan.find(
          self.panchaanga.jd_sunrise[d], self.panchaanga.jd_sunrise[d] + 30, zodiac.SOLAR_NAKSH, 13,
          ayanamsha_id=self.panchaanga.ayanamsha_id).to_tuple()

        moon_magha_jd_start, moon_magha_jd_end = AngaSpan.find(
          sun_hasta_jd_start - 2, sun_hasta_jd_end + 2, zodiac.NAKSHATRAM, 10,
          ayanamsha_id=self.panchaanga.ayanamsha_id).to_tuple()
        if all([moon_magha_jd_start, moon_magha_jd_end]):
          t28_start, t28_end = AngaSpan.find(
            moon_magha_jd_start - 3, moon_magha_jd_end + 3, zodiac.TITHI, 28,
            ayanamsha_id=self.panchaanga.ayanamsha_id).to_tuple()

        moon_hasta_jd_start, moon_hasta_jd_end = AngaSpan.find(
          sun_hasta_jd_start - 1, sun_hasta_jd_end + 1, zodiac.NAKSHATRAM, 13,
          ayanamsha_id=self.panchaanga.ayanamsha_id).to_tuple()
        if all([moon_hasta_jd_start, moon_hasta_jd_end]):
          t30_start, t30_end = AngaSpan.find(
            sun_hasta_jd_start - 1, sun_hasta_jd_end + 1, zodiac.TITHI, 30,
            ayanamsha_id=self.panchaanga.ayanamsha_id).to_tuple()

        gc_28 = gc_30 = False

        if all([sun_hasta_jd_start, moon_magha_jd_start, t28_start]):
          # We have a GC yoga
          gc_28_start = max(sun_hasta_jd_start, moon_magha_jd_start, t28_start)
          gc_28_end = min(sun_hasta_jd_end, moon_magha_jd_end, t28_end)

          if gc_28_start < gc_28_end:
            gc_28 = True

        if all([sun_hasta_jd_start, moon_hasta_jd_start, t30_start]):
          # We have a GC yoga
          gc_30_start = max(sun_hasta_jd_start, moon_hasta_jd_start, t30_start)
          gc_30_end = min(sun_hasta_jd_end, moon_hasta_jd_end, t30_end)

          if gc_30_start < gc_30_end:
            gc_30 = True

      if self.panchaanga.solar_month[d] == 6 and (gc_28 or gc_30):
        if gc_28:
          gc_28_start += tz_off / 24.0
          gc_28_end += tz_off / 24.0
          # sys.stderr.write('28: (%f, %f)\n' % (gc_28_start, gc_28_end))
          gc_28_d = 1 + floor(gc_28_start - self.panchaanga.jd_start_utc)
          t1 = Hour(temporal.jd_to_utc_gregorian(gc_28_start)[3]).toString(format=self.panchaanga.fmt)

          if floor(gc_28_end - 0.5) != floor(gc_28_start - 0.5):
            # -0.5 is for the fact that julday is zero at noon always, not midnight!
            offset = 24
          else:
            offset = 0
          t2 = Hour(temporal.jd_to_utc_gregorian(gc_28_end)[3] + offset).toString(format=self.panchaanga.fmt)
          # sys.stderr.write('gajacchhaya %d\n' % gc_28_d)

          self.panchaanga.fest_days['gajacchAyA-yOgaH' +
                         '-\\textsf{' + t1 + '}{\\RIGHTarrow}\\textsf{' +
                         t2 + '}'] = [gc_28_d]
          gc_28 = False
        if gc_30:
          gc_30_start += tz_off / 24.0
          gc_30_end += tz_off / 24.0
          # sys.stderr.write('30: (%f, %f)\n' % (gc_30_start, gc_30_end))
          gc_30_d = 1 + floor(gc_30_start - self.panchaanga.jd_start_utc)
          t1 = Hour(temporal.jd_to_utc_gregorian(gc_30_start)[3]).toString(format=self.panchaanga.fmt)

          if floor(gc_30_end - 0.5) != floor(gc_30_start - 0.5):
            offset = 24
          else:
            offset = 0
          t2 = Hour(temporal.jd_to_utc_gregorian(gc_30_end)[3] + offset).toString(format=self.panchaanga.fmt)
          # sys.stderr.write('gajacchhaya %d\n' % gc_30_d)

          self.panchaanga.fest_days['gajacchAyA-yOgaH' +
                         '-\\textsf{' + t1 + '}{\\RIGHTarrow}\\textsf{' +
                         t2 + '}'] = [gc_30_d]
          gc_30 = False

  def assign_mahodaya_ardhodaya(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = temporal.jd_to_utc_gregorian(self.panchaanga.jd_start_utc + d - 1)

      # MAHODAYAM
      # Can also refer youtube video https://youtu.be/0DBIwb7iaLE?list=PL_H2LUtMCKPjh63PRk5FA3zdoEhtBjhzj&t=6747
      # 4th pada of vyatipatam, 1st pada of Amavasya, 2nd pada of Shravana, Suryodaya, Bhanuvasara = Ardhodayam
      # 4th pada of vyatipatam, 1st pada of Amavasya, 2nd pada of Shravana, Suryodaya, Somavasara = Mahodayam
      sunrise_zodiac = NakshatraDivision(self.panchaanga.jd_sunrise[d], ayanamsha_id=self.panchaanga.ayanamsha_id)
      sunset_zodiac = NakshatraDivision(self.panchaanga.jd_sunset[d], ayanamsha_id=self.panchaanga.ayanamsha_id)
      if self.panchaanga.lunar_month[d] in [10, 11] and self.panchaanga.tithi_sunrise[d] == 30 or sunrise_zodiac.get_tithi() == 30:
        if sunrise_zodiac.get_angam(zodiac.YOGA) == 17 or \
            sunset_zodiac.get_angam(zodiac.YOGA) == 17 and \
            sunrise_zodiac.get_angam(zodiac.NAKSHATRAM) == 22 or \
            sunset_zodiac.get_angam(zodiac.NAKSHATRAM) == 22:
          if self.panchaanga.weekday[d] == 1:
            festival_name = 'mahOdaya-puNyakAlaH'
            self.add_festival(festival_name, d, debug_festivals)
            # logging.debug('* %d-%02d-%02d> %s!' % (y, m, dt, festival_name))
          elif self.panchaanga.weekday[d] == 0:
            festival_name = 'ardhOdaya-puNyakAlaH'
            self.add_festival(festival_name, d, debug_festivals)
            # logging.debug('* %d-%02d-%02d> %s!' % (y, m, dt, festival_name))