"""Serializers for click analytics responses."""

from rest_framework import serializers


class URLAggregateStatsSerializer(serializers.Serializer):
    """Aggregated click statistics for a single URL."""

    total_clicks = serializers.IntegerField()
    unique_countries = serializers.IntegerField()
    top_referer = serializers.CharField()
    last_clicked_at = serializers.DateTimeField(allow_null=True)


class CountryStatsSerializer(serializers.Serializer):
    """Click breakdown by country."""

    country = serializers.CharField()
    clicks = serializers.IntegerField()
    percentage = serializers.FloatField()


class ReferrerStatsSerializer(serializers.Serializer):
    """Click breakdown by referer."""

    referer = serializers.CharField()
    clicks = serializers.IntegerField()
    percentage = serializers.FloatField()


class HourlyDistributionSerializer(serializers.Serializer):
    """Click distribution by hour of day."""

    hour = serializers.IntegerField()
    clicks = serializers.IntegerField()


class ClickRecordSerializer(serializers.Serializer):
    """Individual click record."""

    id = serializers.IntegerField()
    ip_address = serializers.CharField(allow_null=True)
    country = serializers.CharField()
    referer = serializers.CharField()
    clicked_at = serializers.DateTimeField()


class TimeSeriesPointSerializer(serializers.Serializer):
    """A single day's click count."""

    date = serializers.CharField()
    clicks = serializers.IntegerField()


class AnalyticsSummarySerializer(serializers.Serializer):
    """Full analytics summary for a URL."""

    url_id = serializers.IntegerField(allow_null=True)
    short_code = serializers.CharField()
    stats = URLAggregateStatsSerializer()
    countries = CountryStatsSerializer(many=True)
    referrers = ReferrerStatsSerializer(many=True)
    hourly_distribution = HourlyDistributionSerializer(many=True)
    recent_clicks = ClickRecordSerializer(many=True)
    time_series = TimeSeriesPointSerializer(many=True)
