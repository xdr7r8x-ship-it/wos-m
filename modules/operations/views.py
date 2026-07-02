"""
WOS-M Operations Panel - Views

This module provides the Discord UI for the Operations Control Panel.
"""

import discord
from typing import Optional

from core.permissions import PermissionLevel


class OperationsPanelView(discord.ui.View):
    """Main Operations Control Panel view."""
    
    def __init__(self, owner_id: Optional[int] = None):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        
        # Row 1: Health & Metrics
        self.add_item(HealthCheckButton(label="💚 Health Check", custom_id="ops_health_check", style=discord.ButtonStyle.success))
        self.add_item(MetricsButton(label="📊 Metrics", custom_id="ops_metrics", style=discord.ButtonStyle.primary))
        
        # Row 2: Incidents & Alerts
        self.add_item(IncidentsButton(label="🚨 Incidents", custom_id="ops_incidents", style=discord.ButtonStyle.danger))
        self.add_item(AlertsButton(label="🔔 Alerts", custom_id="ops_alerts", style=discord.ButtonStyle.secondary))
        
        # Row 3: Backup & Restore
        self.add_item(BackupButton(label="💾 Backup", custom_id="ops_backup", style=discord.ButtonStyle.primary))
        self.add_item(RestoreButton(label="↩️ Rollback", custom_id="ops_rollback", style=discord.ButtonStyle.secondary))
        
        # Row 4: Upgrades & Self-Healing
        self.add_item(UpgradeButton(label="🚀 Upgrade", custom_id="ops_upgrade", style=discord.ButtonStyle.primary))
        self.add_item(SelfHealingButton(label="🧰 Self-Heal", custom_id="ops_self_heal", style=discord.ButtonStyle.secondary))
        
        # Row 5: Reports & Settings
        self.add_item(ReportsButton(label="📄 Reports", custom_id="ops_reports", style=discord.ButtonStyle.secondary))
        self.add_item(SettingsButton(label="⚙️ Settings", custom_id="ops_settings", style=discord.ButtonStyle.secondary))


class HealthCheckButton(discord.ui.Button):
    """Button to run health check."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.health import run_full_health_check
        
        try:
            report = await run_full_health_check()
            
            status_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "unhealthy": "❌"
            }.get(report.overall_status.value, "❓")
            
            embed = discord.Embed(
                title=f"{status_emoji} Health Check Report",
                color=0x2ecc71 if report.overall_status.value == "healthy" else 0xf39c12 if report.overall_status.value == "degraded" else 0xe74c3c
            )
            
            embed.add_field(
                name="Status",
                value=f"**{report.overall_status.value.upper()}**",
                inline=True
            )
            embed.add_field(
                name="Version",
                value=report.version,
                inline=True
            )
            embed.add_field(
                name="Uptime",
                value=f"{report.uptime_seconds:.0f}s",
                inline=True
            )
            
            failed_checks = [c for c in report.checks if c.status == "fail"]
            if failed_checks:
                check_list = "\n".join([f"❌ {c.name}: {c.message_en}" for c in failed_checks[:5]])
                embed.add_field(
                    name="Failed Checks",
                    value=check_list[:1024],
                    inline=False
                )
            
            embed.add_field(
                name="Passed Checks",
                value=f"{len([c for c in report.checks if c.status == 'pass'])}/{len(report.checks)}",
                inline=True
            )
            
            if report.suggested_action:
                embed.add_field(
                    name="Suggested Action",
                    value=report.suggested_action,
                    inline=False
                )
            
            embed.set_footer(text=f"Checked at {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Health check failed: {str(e)}",
                ephemeral=True
            )


class MetricsButton(discord.ui.Button):
    """Button to show metrics."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.metrics import get_metrics_collector
        
        try:
            collector = get_metrics_collector()
            snapshot = collector.collect_snapshot()
            metrics_text = collector.format_metrics(snapshot)
            
            # Parse and format as embed
            lines = metrics_text.split('\n')
            embed = discord.Embed(
                title="📊 Metrics Dashboard",
                color=0x3498db
            )
            
            # Add fields
            uptime = collector.get_uptime_formatted()
            embed.add_field(
                name="⏱️ Uptime",
                value=uptime,
                inline=True
            )
            embed.add_field(
                name="🎮 Commands",
                value=str(snapshot.commands),
                inline=True
            )
            embed.add_field(
                name="🔄 Interactions",
                value=str(snapshot.interactions),
                inline=True
            )
            embed.add_field(
                name="❌ Failed",
                value=str(snapshot.failed_interactions),
                inline=True
            )
            embed.add_field(
                name="📈 Success Rate",
                value=f"{snapshot.success_rate}%",
                inline=True
            )
            embed.add_field(
                name="⚡ Avg Callback",
                value=f"{snapshot.avg_callback_duration_ms}ms",
                inline=True
            )
            embed.add_field(
                name="🗄️ DB Errors",
                value=str(snapshot.db_errors),
                inline=True
            )
            embed.add_field(
                name="🚨 Open Incidents",
                value=str(snapshot.open_incidents),
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to get metrics: {str(e)}",
                ephemeral=True
            )


class IncidentsButton(discord.ui.Button):
    """Button to show incidents."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.incident_reports import get_incident_manager
        
        try:
            manager = get_incident_manager()
            open_incidents = await manager.list_open_incidents(limit=10)
            
            embed = discord.Embed(
                title="🚨 Open Incidents",
                color=0xe74c3c if open_incidents else 0x2ecc71
            )
            
            if open_incidents:
                for inc in open_incidents:
                    severity_emoji = {
                        "critical": "🔴",
                        "error": "🟠",
                        "warning": "🟡",
                        "info": "🔵"
                    }.get(inc.severity.value, "⚪")
                    
                    embed.add_field(
                        name=f"{severity_emoji} {inc.id}",
                        value=f"**{inc.message[:100]}**\nSource: {inc.source}\nOccurrences: {inc.occurrence_count}",
                        inline=False
                    )
            else:
                embed.description = "✅ No open incidents"
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to get incidents: {str(e)}",
                ephemeral=True
            )


class AlertsButton(discord.ui.Button):
    """Button to manage alerts."""
    async def callback(self, interaction: discord.Interaction):
        view = AlertsConfigView()
        embed = discord.Embed(
            title="🔔 Alert Configuration",
            description="Configure alert settings and test alerts",
            color=0x9b59b6
        )
        embed.add_field(
            name="Current Settings",
            value="• Alerts: Enabled\n• Cooldown: 5 minutes\n• Owner: Configured",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AlertsConfigView(discord.ui.View):
    """View for configuring alerts."""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(TestAlertButton(label="🧪 Test Alert", custom_id="ops_alert_test"))
        self.add_item(ToggleAlertsButton(label="🔇 Toggle Alerts", custom_id="ops_alert_toggle"))


class TestAlertButton(discord.ui.Button):
    """Test alert button."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.alerts import AlertManager
        
        try:
            manager = AlertManager.get_instance()
            success = await manager.test_alert()
            
            if success:
                await interaction.response.send_message(
                    "✅ Test alert sent! Check your DMs.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "⚠️ Could not send test alert. Check bot is connected and owner ID is configured.",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class ToggleAlertsButton(discord.ui.Button):
    """Toggle alerts button."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.alerts import AlertManager
        
        try:
            manager = AlertManager.get_instance()
            current = manager.is_enabled()
            manager.set_enabled(not current)
            
            status = "disabled" if not current else "enabled"
            await interaction.response.send_message(
                f"🔔 Alerts {status}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class BackupButton(discord.ui.Button):
    """Button to create/view backups."""
    async def callback(self, interaction: discord.Interaction):
        view = BackupView()
        embed = discord.Embed(
            title="💾 Backup Management",
            description="Create and manage backups",
            color=0x3498db
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class BackupView(discord.ui.View):
    """View for backup operations."""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(CreateBackupButton(label="➕ Create Backup", custom_id="ops_backup_create"))
        self.add_item(ListBackupsButton(label="📋 List Backups", custom_id="ops_backup_list"))
        self.add_item(VerifyBackupButton(label="✅ Verify Backup", custom_id="ops_backup_verify"))


class CreateBackupButton(discord.ui.Button):
    """Create backup button."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.backup import get_backup_manager
        from core.operations.audit import audit_log, AuditAction, RiskLevel
        
        try:
            manager = get_backup_manager()
            success, msg, metadata = await manager.create_backup(
                name=f"manual_{interaction.user.id}"
            )
            
            # Audit log
            await audit_log(
                user_id=str(interaction.user.id),
                action=AuditAction.BACKUP_CREATE,
                module="operations",
                target=metadata.id if metadata else None,
                status="success" if success else "failure",
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                risk_level=RiskLevel.HIGH
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Backup Created",
                    description=f"**ID:** `{metadata.id}`\n**Size:** {metadata.size_bytes} bytes",
                    color=0x2ecc71
                )
            else:
                embed = discord.Embed(
                    title="❌ Backup Failed",
                    description=msg,
                    color=0xe74c3c
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class ListBackupsButton(discord.ui.Button):
    """List backups button."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.backup import get_backup_manager
        
        try:
            manager = get_backup_manager()
            backups = await manager.list_backups(limit=10)
            
            embed = discord.Embed(
                title="📋 Available Backups",
                color=0x3498db
            )
            
            if backups:
                for backup in backups:
                    embed.add_field(
                        name=f"💾 {backup.name}",
                        value=f"ID: `{backup.id}`\nSize: {backup.size_bytes} bytes\nCreated: {backup.created_at.strftime('%Y-%m-%d %H:%M')}",
                        inline=False
                    )
            else:
                embed.description = "No backups available"
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class VerifyBackupButton(discord.ui.Button):
    """Verify backup button."""
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "⚠️ Please use the rollback button to select a backup to verify.",
            ephemeral=True
        )


class RestoreButton(discord.ui.Button):
    """Button for rollback operations."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.rollback import get_rollback_manager
        
        try:
            manager = get_rollback_manager()
            points = await manager.list_restore_points(limit=10)
            
            embed = discord.Embed(
                title="↩️ Rollback",
                description=manager.format_restore_points(points),
                color=0xf39c12
            )
            
            view = RollbackView(points)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class RollbackView(discord.ui.View):
    """View for rollback operations."""
    
    def __init__(self, points):
        super().__init__(timeout=300)
        self.points = points
        
        for point in points[:5]:
            self.add_item(
                RollbackSelectButton(
                    label=f"↩️ {point.id[:20]}",
                    custom_id=f"ops_rollback_{point.id}",
                    point_id=point.id
                )
            )


class RollbackSelectButton(discord.ui.Button):
    """Select backup for rollback."""
    
    def __init__(self, label, custom_id, point_id):
        super().__init__(label=label, custom_id=custom_id, style=discord.ButtonStyle.danger)
        self.point_id = point_id
    
    async def callback(self, interaction: discord.Interaction):
        from core.operations.rollback import get_rollback_manager
        from core.operations.audit import audit_log, AuditAction, RiskLevel
        
        # Send confirmation
        embed = discord.Embed(
            title="⚠️ Confirm Rollback",
            description=f"Are you sure you want to rollback to:\n`{self.point_id}`\n\nThis action requires explicit confirmation.",
            color=0xe74c3c
        )
        
        view = RollbackConfirmView(self.point_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RollbackConfirmView(discord.ui.View):
    """Confirmation view for rollback."""
    
    def __init__(self, point_id):
        super().__init__(timeout=60)
        self.point_id = point_id
        self.add_item(RollbackConfirmButton(label="✅ Confirm Rollback", custom_id=f"ops_rollback_confirm_{point_id}", style=discord.ButtonStyle.danger))
        self.add_item(RollbackCancelButton(label="❌ Cancel", custom_id="ops_rollback_cancel", style=discord.ButtonStyle.secondary))


class RollbackConfirmButton(discord.ui.Button):
    """Confirm rollback."""
    
    def __init__(self, label, custom_id, style):
        super().__init__(label=label, custom_id=custom_id, style=style)
    
    async def callback(self, interaction: discord.Interaction):
        from core.operations.rollback import get_rollback_manager
        
        try:
            manager = get_rollback_manager()
            point_id = self.custom_id.replace("ops_rollback_confirm_", "")
            
            success, msg = await manager.rollback_to_backup(point_id, confirmation=True)
            
            if success:
                embed = discord.Embed(
                    title="✅ Rollback Complete",
                    description=msg,
                    color=0x2ecc71
                )
            else:
                embed = discord.Embed(
                    title="❌ Rollback Failed",
                    description=msg,
                    color=0xe74c3c
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class RollbackCancelButton(discord.ui.Button):
    """Cancel rollback."""
    
    def __init__(self, label, custom_id, style):
        super().__init__(label=label, custom_id=custom_id, style=style)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "✅ Rollback cancelled",
            ephemeral=True
        )


class UpgradeButton(discord.ui.Button):
    """Button for upgrade operations."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.upgrades import get_upgrade_manager
        
        try:
            manager = get_upgrade_manager()
            plan = await manager.plan_upgrade()
            
            report = manager.generate_upgrade_report(plan)
            
            embed = discord.Embed(
                title="🚀 Upgrade Plan",
                description=report,
                color=0x3498db
            )
            
            view = UpgradeView()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class UpgradeView(discord.ui.View):
    """View for upgrade operations."""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(PreUpgradeCheckButton(label="🔍 Pre-Upgrade Check", custom_id="ops_upgrade_check"))
        self.add_item(ApplyUpgradeButton(label="🚀 Apply Upgrade", custom_id="ops_upgrade_apply", style=discord.ButtonStyle.danger))


class PreUpgradeCheckButton(discord.ui.Button):
    """Run pre-upgrade checks."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.upgrades import get_upgrade_manager
        
        try:
            manager = get_upgrade_manager()
            checks_passed, results = await manager.run_pre_upgrade_checks()
            
            embed = discord.Embed(
                title="🔍 Pre-Upgrade Checks",
                color=0x2ecc71 if checks_passed else 0xe74c3c
            )
            
            for result in results:
                icon = "✅" if result.status == "pass" else "❌" if result.status == "fail" else "⚠️"
                embed.add_field(
                    name=f"{icon} {result.step.value}",
                    value=result.message,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class ApplyUpgradeButton(discord.ui.Button):
    """Apply upgrade button."""
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "⚠️ **Owner confirmation required for upgrades.**\n\nPlease use `/upgrade` command with owner permissions to apply upgrades.",
            ephemeral=True
        )


class SelfHealingButton(discord.ui.Button):
    """Button for self-healing operations."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.self_healing import get_self_healing_engine
        
        try:
            engine = get_self_healing_engine()
            stats = engine.get_recovery_stats()
            
            embed = discord.Embed(
                title="🧰 Self-Healing Configuration",
                color=0x3498db
            )
            
            embed.add_field(
                name="Status",
                value="Enabled" if stats['policy_enabled'] else "Disabled",
                inline=True
            )
            embed.add_field(
                name="Total Attempts",
                value=str(stats['total_attempts']),
                inline=True
            )
            embed.add_field(
                name="Success Rate",
                value=f"{stats['success_rate']}%",
                inline=True
            )
            embed.add_field(
                name="Allowed Actions",
                value=", ".join(stats['allowed_actions'][:5]) + "...",
                inline=False
            )
            
            view = SelfHealingConfigView()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class SelfHealingConfigView(discord.ui.View):
    """View for self-healing configuration."""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ToggleSelfHealingButton(label="🔄 Toggle Self-Heal", custom_id="ops_self_heal_toggle"))
        self.add_item(RunSelfHealButton(label="🧰 Run Recovery", custom_id="ops_self_heal_run"))


class ToggleSelfHealingButton(discord.ui.Button):
    """Toggle self-healing."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.self_healing import get_self_healing_engine
        
        try:
            engine = get_self_healing_engine()
            policy = engine.get_policy()
            engine.update_policy(enabled=not policy.enabled)
            
            status = "disabled" if policy.enabled else "enabled"
            await interaction.response.send_message(
                f"🧰 Self-healing {status}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed: {str(e)}",
                ephemeral=True
            )


class RunSelfHealButton(discord.ui.Button):
    """Run self-healing."""
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🧰 Self-healing runs automatically when issues are detected. Use Health Check to trigger a manual review.",
            ephemeral=True
        )


class ReportsButton(discord.ui.Button):
    """Button for reports."""
    async def callback(self, interaction: discord.Interaction):
        view = ReportsView()
        embed = discord.Embed(
            title="📄 Reports",
            description="Generate various system reports",
            color=0x3498db
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ReportsView(discord.ui.View):
    """View for report generation."""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(DailyHealthReportButton(label="🏥 Daily Health", custom_id="ops_report_health"))
        self.add_item(IncidentReportButton(label="🚨 Incidents", custom_id="ops_report_incidents"))
        self.add_item(ReleaseReportButton(label="🚀 Release", custom_id="ops_report_release"))


class DailyHealthReportButton(discord.ui.Button):
    """Generate daily health report."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.health import run_full_health_check
        
        try:
            report = await run_full_health_check()
            
            embed = discord.Embed(
                title="🏥 Daily Health Report",
                color=0x2ecc71,
                timestamp=report.timestamp
            )
            
            embed.add_field(name="Status", value=report.overall_status.value.upper(), inline=True)
            embed.add_field(name="Passed", value=f"{len([c for c in report.checks if c.status == 'pass'])}", inline=True)
            embed.add_field(name="Failed", value=f"{len([c for c in report.checks if c.status == 'fail'])}", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {str(e)}", ephemeral=True)


class IncidentReportButton(discord.ui.Button):
    """Generate incident report."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.incident_reports import get_incident_manager
        
        try:
            manager = get_incident_manager()
            report = await manager.generate_daily_incident_report()
            
            await interaction.response.send_message(
                f"```\n{report}\n```",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {str(e)}", ephemeral=True)


class ReleaseReportButton(discord.ui.Button):
    """Generate release report."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.versioning import get_version_manager
        
        try:
            vm = get_version_manager()
            notes = vm.generate_release_notes()
            
            await interaction.response.send_message(
                f"```\n{notes}\n```",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {str(e)}", ephemeral=True)


class SettingsButton(discord.ui.Button):
    """Button for operations settings."""
    async def callback(self, interaction: discord.Interaction):
        view = OperationsSettingsView()
        embed = discord.Embed(
            title="⚙️ Operations Settings",
            description="Configure operations system settings",
            color=0x3498db
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OperationsSettingsView(discord.ui.View):
    """View for operations settings."""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SchedulerToggleButton(label="📅 Scheduler", custom_id="ops_settings_scheduler"))
        self.add_item(BackupRetentionButton(label="💾 Backup Retention", custom_id="ops_settings_backup_retention"))


class SchedulerToggleButton(discord.ui.Button):
    """Toggle scheduler."""
    async def callback(self, interaction: discord.Interaction):
        from core.operations.scheduler import get_scheduler
        
        try:
            scheduler = get_scheduler()
            scheduler.set_enabled(not scheduler.is_enabled())
            
            await interaction.response.send_message(
                f"📅 Scheduler {'enabled' if scheduler.is_enabled() else 'disabled'}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {str(e)}", ephemeral=True)


class BackupRetentionButton(discord.ui.Button):
    """Set backup retention."""
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "💾 Backup retention is set via `OPS_BACKUP_RETENTION_DAYS` environment variable (default: 14 days)",
            ephemeral=True
        )
