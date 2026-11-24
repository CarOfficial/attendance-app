package com.attendance.app.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.attendance.app.ui.theme.Palette

/** Soft royal backdrop with gold light, drawn behind everything. */
@Composable
fun AuroraBackground(content: @Composable () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Palette.Background)
            .drawBehind {
                val w = size.width
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Palette.Purple500.copy(alpha = 0.32f), Color.Transparent),
                        center = Offset(0f, 0f),
                        radius = w * 0.9f,
                    ),
                    radius = w * 0.9f,
                    center = Offset(0f, 0f),
                )
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Palette.Gold500.copy(alpha = 0.22f), Color.Transparent),
                        center = Offset(w, 0f),
                        radius = w * 0.8f,
                    ),
                    radius = w * 0.8f,
                    center = Offset(w, 0f),
                )
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Palette.Purple600.copy(alpha = 0.25f), Color.Transparent),
                        center = Offset(w * 0.5f, size.height),
                        radius = w * 1.0f,
                    ),
                    radius = w * 1.0f,
                    center = Offset(w * 0.5f, size.height),
                )
            },
    ) {
        content()
    }
}

/** A frosted surface: translucent white, light border, soft purple shadow. */
@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    strong: Boolean = false,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(28.dp)
    Column(
        modifier = modifier
            .shadow(
                elevation = 18.dp,
                shape = shape,
                ambientColor = Palette.Purple900.copy(alpha = 0.25f),
                spotColor = Palette.Purple900.copy(alpha = 0.35f),
            )
            .clip(shape)
            .background(Color.White.copy(alpha = if (strong) 0.85f else 0.62f))
            .border(1.dp, Color.White.copy(alpha = 0.85f), shape)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        content = content,
    )
}

@Composable
fun GradientButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    gold: Boolean = false,
) {
    val shape = RoundedCornerShape(20.dp)
    val colors: List<Color> = if (gold) {
        listOf(Palette.Gold300, Palette.Gold500, Palette.Gold600)
    } else {
        listOf(Palette.Purple500, Palette.Purple600, Palette.Purple900)
    }
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(56.dp)
            .shadow(
                elevation = 12.dp,
                shape = shape,
                ambientColor = Palette.Purple700.copy(alpha = 0.4f),
                spotColor = Palette.Purple700.copy(alpha = 0.5f),
            )
            .clip(shape)
            .background(Brush.linearGradient(colors))
            .alpha(if (enabled) 1f else 0.55f)
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = if (gold) Color(0xFF3B2A04) else Color.White,
            style = MaterialTheme.typography.titleMedium,
        )
    }
}

/** The big round check-in / check-out button with a soft pulsing halo. */
@Composable
fun CheckOrb(
    label: String,
    sublabel: String,
    isCheckOut: Boolean,
    busy: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val transition = rememberInfiniteTransition(label = "halo")
    val pulse by transition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.6f,
        animationSpec = infiniteRepeatable(tween(1600), RepeatMode.Reverse),
        label = "pulse",
    )

    val colors: List<Color> = if (isCheckOut) {
        listOf(Color(0xFFFB7185), Color(0xFFE11D48), Color(0xFF9F1239))
    } else {
        listOf(Palette.Purple400, Palette.Purple600, Palette.Purple900)
    }
    val halo = if (isCheckOut) Color(0xFFFB7185) else Palette.Purple500

    Box(modifier = Modifier.size(260.dp), contentAlignment = Alignment.Center) {
        Box(
            modifier = Modifier
                .size(240.dp)
                .alpha(if (busy) 0.15f else pulse)
                .background(Brush.radialGradient(listOf(halo, Color.Transparent)), CircleShape),
        )
        Box(
            modifier = Modifier
                .size(200.dp)
                .shadow(
                    elevation = 24.dp,
                    shape = CircleShape,
                    ambientColor = halo.copy(alpha = 0.5f),
                    spotColor = halo.copy(alpha = 0.6f),
                )
                .clip(CircleShape)
                .background(Brush.linearGradient(colors))
                .border(1.dp, Color.White.copy(alpha = 0.25f), CircleShape)
                .alpha(if (enabled) 1f else 0.7f)
                .clickable(enabled = enabled && !busy, onClick = onClick),
            contentAlignment = Alignment.Center,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = if (busy) "…" else label,
                    color = Color.White,
                    style = MaterialTheme.typography.headlineSmall,
                )
                Text(
                    text = sublabel,
                    color = Color.White.copy(alpha = 0.85f),
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}

@Composable
fun StatusPill(text: String, tone: StatusTone) {
    val (bg, fg) = when (tone) {
        StatusTone.Waiting -> Palette.Gold100 to Palette.Gold600
        StatusTone.Working -> Color(0xFFD1FAE5) to Palette.Emerald600
        StatusTone.Done -> Palette.Purple100 to Palette.Purple800
        StatusTone.Bad -> Color(0xFFFFE4E6) to Palette.Rose600
        StatusTone.Neutral -> Color(0xFFF1F5F9) to Color(0xFF475569)
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(50))
            .background(bg)
            .border(1.dp, fg.copy(alpha = 0.25f), RoundedCornerShape(50))
            .padding(horizontal = 16.dp, vertical = 8.dp),
    ) {
        Text(text = text, color = fg, style = MaterialTheme.typography.labelLarge)
    }
}

enum class StatusTone { Waiting, Working, Done, Bad, Neutral }

@Composable
fun TimeTile(label: String, value: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(20.dp))
            .background(Color.White.copy(alpha = 0.6f))
            .border(1.dp, Color.White.copy(alpha = 0.8f), RoundedCornerShape(20.dp))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
        Text(value, style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
    }
}

/** Filled version used for the "notice" banner after an action. */
@Composable
fun NoticeBanner(text: String, isError: Boolean) {
    val fg = if (isError) Palette.Rose600 else Palette.Emerald600
    val bg = if (isError) Color(0xFFFFF1F2) else Color(0xFFECFDF5)
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(bg.copy(alpha = 0.9f))
            .border(1.dp, fg.copy(alpha = 0.25f), RoundedCornerShape(18.dp))
            .padding(16.dp),
    ) {
        Text(text = text, color = fg, style = MaterialTheme.typography.bodyMedium)
    }
}

