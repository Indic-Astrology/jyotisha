from indic_transliteration import xsanscript
from jyotisha.panchaanga.spatio_temporal import City
from jyotisha.panchaanga.temporal import names, AngaType
from jyotisha.panchaanga.temporal.festival import rules
from jyotisha.panchaanga.temporal.festival.rules import RulesRepo

ujjain = City.get_city_from_db(name="Ujjain")


def to_table_dict(panchaanga, script=xsanscript.DEVANAGARI):
  final_dict = {"data": []}
  rules_collection = rules.RulesCollection.get_cached(
    repos_tuple=tuple(panchaanga.computation_system.festival_options.repos), julian_handling=panchaanga.computation_system.festival_options.julian_handling)
  for daily_panchaanga in panchaanga.daily_panchaangas_sorted(skip_padding_days=True):
    day_dict = {}
    day_dict["gregorian"] = daily_panchaanga.date.get_date_str()
    day_dict["islamic"] = daily_panchaanga.date.to_islamic_date().get_date_str()
    day_dict["islamic_month"] = daily_panchaanga.get_month_str(month_type=RulesRepo.ISLAMIC_MONTH_DIR, script=script)
    day_dict["Indian_civil"] = daily_panchaanga.date.to_indian_civil_date().get_date_str()
    day_dict["lunar"] = daily_panchaanga.get_date(month_type=RulesRepo.LUNAR_MONTH_DIR).get_date_str()
    day_dict["lunar_month"] = daily_panchaanga.get_month_str(month_type=RulesRepo.LUNAR_MONTH_DIR, script=script)
    day_dict["lunar_samvatsara"] = daily_panchaanga.get_samvatsara(month_type=RulesRepo.LUNAR_MONTH_DIR).get_name(script=script)
    day_dict["tropical"] = daily_panchaanga.get_date(month_type=RulesRepo.TROPICAL_MONTH_DIR).get_date_str()
    day_dict["tropical_month"] = daily_panchaanga.get_month_str(month_type=RulesRepo.TROPICAL_MONTH_DIR, script=script)
    day_dict["sidereal_solar"] = daily_panchaanga.get_date(month_type=RulesRepo.SIDEREAL_SOLAR_MONTH_DIR).get_date_str()
    day_dict["sidereal_solar"] = daily_panchaanga.get_month_str(month_type=RulesRepo.SIDEREAL_SOLAR_MONTH_DIR, script=script)
    day_dict["vaara"] = names.NAMES['VARA_NAMES']['sa'][script][daily_panchaanga.date.get_weekday()]
    day_dict["lunar_nakshatras"] = daily_panchaanga.sunrise_day_angas.get_anga_data_str(anga_type=AngaType.NAKSHATRA, script=script, reference_jd=daily_panchaanga.julian_day_start)
    day_dict["festivals"] = ", ".join([x.get_full_title(fest_details_dict=rules_collection.name_to_rule) for x in daily_panchaanga.festival_id_to_instance.values()])
    final_dict["data"].append(day_dict)
  return final_dict
